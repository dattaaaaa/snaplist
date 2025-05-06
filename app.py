from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_pymongo import PyMongo
from flask import send_from_directory
import requests
from werkzeug.security import generate_password_hash, check_password_hash
#from bson import ObjectId
from bson.objectid import ObjectId
import os
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO
import base64
from io import BytesIO
from datetime import timedelta
from datetime import datetime
import json
from functools import wraps


def to_ist(utc_dt):
    """Convert UTC datetime to IST (UTC+5:30)"""
    if not utc_dt:
        return utc_dt
    return utc_dt + timedelta(hours=5, minutes=30)

def format_datetime(dt, format_str="%B %d, %Y"):
    """Custom datetime formatting filter"""
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    return dt

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Change this to a secure secret key
app.config["MONGO_URI"] = "mongodb://localhost:27017/snaplist"
mongo = PyMongo(app)
app.jinja_env.filters['to_ist'] = to_ist
app.jinja_env.filters['strftime'] = format_datetime

GROQ_API_KEY = 'YOUR_API_KEY_HERE' 
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama-3.3-70b-versatile'



SYSTEM_PROMPT = """You are a helpful customer service assistant for our retail shopping application that helps users with:

1. Order tracking and details
2. Cancellations and refunds
3. Product information and availability
4. Account management
5. General shopping assistance
6. Technical support for the shopping app

Rules and Capabilities:
- You have access to user's order history, cart items, and account details
- You can help process order cancellations for eligible orders (within 24 hours of placing)
- You can look up product information and check availability
- You provide shipping and delivery information
- You maintain conversation context to avoid repetitive questions
- You cannot modify orders or prices
- You cannot access admin functions or backend operations
- You must verify user identity before providing sensitive information
- You should be friendly, professional and solution-oriented

When handling requests:
- For order queries: require order ID or date range
- For cancellations: verify order is within 24-hour cancellation window
- For product queries: check current product database
- Always verify user has necessary information
- If information is missing, ask for it politely
- Maintain a helpful and customer-focused tone

Product Categories:
1. Fruits & Vegetables
2. Essentials (Healthcare, Personal Care, Beverages)

Delivery Information:
- Standard delivery: 2-3 business days
- Express delivery: Next day delivery
- Delivery fee: 40 INR
- Free delivery on orders above 500 INR
- Delivery times: 9 AM - 9 PM"""


def chat_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_user_context():
    """Get relevant user context for the chatbot"""
    user_id = session['user_id']
    
    # Get all orders for the user
    orders = list(mongo.db.orders.find(
        {'user_id': user_id}
    ).sort('created_at', -1))
    
    # Get cart items
    cart = mongo.db.carts.find_one({'user_id': user_id})
    
    # Get user details
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
    # Format orders with detailed information
    formatted_orders = [{
        'order_id': str(order['_id']),
        'status': order['status'],
        'total': order['total'],
        'date': order['created_at'].isoformat(),
        'items': [{ 
            'product': item['product'],
            'quantity': item['quantity'],
            'price': item.get('price', 0)
        } for item in order.get('order_items', [])],
        'shipping_address': order.get('shipping_address', {}),
        'payment_method': order.get('payment_method', '')
    } for order in orders]
    
    context = {
        'user_email': user['email'],
        'user_name': user['name'],
        'orders': formatted_orders,
        'cart_items': len(cart['items']) if cart and 'items' in cart else 0
    }
    
    return context


# Load YOLO models
model_fruits_vegetables = None
model_checkout = None

# Product database with Indian prices
products_db = {
    # Fruits and Vegetables category
    "fruits_vegetables": {
        "apple": {
            "price": 40,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/102104/pexels-photo-102104.jpeg",
            "description": "Fresh Red Apples"
        },
        "banana": {
            "price": 10,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/2872755/pexels-photo-2872755.jpeg",
            "description": "Ripe Yellow Bananas"
        },
        "bell_pepper": {
            "price": 30,
            "category": "vegetables",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/2893635/pexels-photo-2893635.jpeg",
            "description": "Fresh Bell Peppers"
        },
        "cabbage": {
            "price": 50,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/209482/pexels-photo-209482.jpeg",
            "description": "Green Cabbage"
        },
        "carrot": {
            "price": 60,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/143133/pexels-photo-143133.jpeg",
            "description": "Fresh Carrots"
        },
        "chilli_pepper": {
            "price": 80,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/1374651/pexels-photo-1374651.jpeg",
            "description": "Spicy Chilli Peppers"
        },
        "corn": {
            "price": 20,
            "category": "vegetables",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/547263/pexels-photo-547263.jpeg",
            "description": "Sweet Corn"
        },
        "cucumber": {
            "price": 40,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/2329440/pexels-photo-2329440.jpeg",
            "description": "Fresh Cucumbers"
        },
        "eggplant": {
            "price": 50,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/321551/pexels-photo-321551.jpeg",
            "description": "Purple Eggplants"
        },
        "garlic": {
            "price": 120,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/928251/pexels-photo-928251.jpeg",
            "description": "Fresh Garlic"
        },
        "grape": {
            "price": 100,
            "category": "fruits",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/708777/pexels-photo-708777.jpeg",
            "description": "Juicy Grapes"
        },
        "kiwi": {
            "price": 50,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/51312/kiwi-fruit-vitamins-healthy-eating-51312.jpeg",
            "description": "Fresh Kiwi"
        },
        "lemon": {
            "price": 5,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/1414122/pexels-photo-1414122.jpeg",
            "description": "Fresh Lemons"
        },
        "lettuce": {
            "price": 80,
            "category": "vegetables",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/1199562/pexels-photo-1199562.jpeg",
            "description": "Crisp Lettuce"
        },
        "mango": {
            "price": 100,
            "category": "fruits",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/2294471/pexels-photo-2294471.jpeg",
            "description": "Sweet Mangoes"
        },
        "onion": {
            "price": 40,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/175415/pexels-photo-175415.jpeg",
            "description": "Fresh Onions"
        },
        "orange": {
            "price": 15,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/161559/background-bitter-breakfast-bright-161559.jpeg",
            "description": "Juicy Oranges"
        },
        "pineapple": {
            "price": 100,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/947879/pexels-photo-947879.jpeg",
            "description": "Fresh Pineapple"
        },
        "potato": {
            "price": 30,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/2286776/pexels-photo-2286776.jpeg",
            "description": "Fresh Potatoes"
        },
        "sweetpotato": {
            "price": 40,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/13059602/pexels-photo-13059602.jpeg",
            "description": "Sweet Potatoes"
        },
        "tomato": {
            "price": 40,
            "category": "vegetables",
            "unit": "per kg",
            "image": "https://images.pexels.com/photos/533280/pexels-photo-533280.jpeg",
            "description": "Fresh Tomatoes"
        },
        "watermelon": {
            "price": 80,
            "category": "fruits",
            "unit": "per piece",
            "image": "https://images.pexels.com/photos/2894205/pexels-photo-2894205.jpeg",
            "description": "Juicy Watermelon"
        }
    },
    # Essentials category
    "essentials": {
        "4D_medical_face-mask": {
            "price": 150,
            "category": "healthcare",
            "unit": "per box",
            "image": "https://images.pexels.com/photos/4197564/pexels-photo-4197564.jpeg",
            "description": "Medical Face Masks (Pack of 50)"
        },
        "Let-green_alcohol_wipes": {
            "price": 100,
            "category": "healthcare",
            "unit": "per pack",
            "image": "https://images.pexels.com/photos/8891202/pexels-photo-8891202.jpeg",
            "description": "Alcohol Wipes for Sanitization"
        },
        "X-men": {
            "price": 200,
            "category": "personal_care",
            "unit": "per item",
            "image": "https://medias.watsons.vn/publishing/WTCVN-216354-front-prodcat.jpg",
            "description": "X-Men Personal Care Product"
        },
        "aquafina": {
            "price": 20,
            "category": "beverages",
            "unit": "per bottle",
            "image": "https://irp.cdn-website.com/md/pexels/dms3rep/multi/pexels-photo-9258371.jpeg",
            "description": "Aquafina Mineral Water"
        },
        "life-buoy": {
            "price": 45,
            "category": "personal_care",
            "unit": "per item",
            "image": "https://img.watsonsvn.com/ecommerce/ecom/Lifebuoy/Lifebuoy-Anti-Bacterial-Hand-Wash-Total-10-450g-2.jpg",
            "description": "Lifebuoy Hand Sanitizer"
        },
        "luong_kho": {
            "price": 80,
            "category": "snacks",
            "unit": "per pack",
            "image": "https://cdn2.fptshop.com.vn/unsafe/Uploads/images/tin-tuc/162896/Originals/lu%CC%9Bo%CC%9Bng%20kho%CC%82%2002(1).jpg",
            "description": "Luong Kho Snacks"
        },
        "milo": {
            "price": 120,
            "category": "beverages",
            "unit": "per pack",
            "image": "https://spencil.vn/wp-content/uploads/2024/07/thiet-ke-bao-bi-Milo-SPencil-Agency-1.png",
            "description": "Milo Chocolate Drink"
        },
        "teppy_orange_juice": {
            "price": 90,
            "category": "beverages",
            "unit": "per bottle",
            "image": "https://cdn.tgdd.vn/Files/2021/02/05/1325829/thanh-loc-lan-da-cho-ngay-tet-them-xinh-voi-cac-loai-nuoc-ep-cam-202201171029377144.jpg",
            "description": "Teppy Orange Juice"
        }
    }
}

def load_models():
    global model_fruits_vegetables, model_checkout
    if model_fruits_vegetables is None:
        model_fruits_vegetables = YOLO("fruits_vegetables.pt")
    if model_checkout is None:
        model_checkout = YOLO("retail_product.pt")


def process_image(image_data, category):
    try:
        image = Image.open(BytesIO(image_data))
        image_cv = np.array(image)
        if image_cv.shape[-1] == 4:
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGBA2RGB)

        load_models()
        
        # Select model based on category
        model = model_fruits_vegetables if category == 'fruits_vegetables' else model_checkout
        results = model.predict(image_cv, save=False, save_txt=False)

        detected_items = []
        for box in results[0].boxes:
            cls = int(box.cls)
            conf = float(box.conf)
            label = model.names[cls]
            if label != "cart":
                # Convert label to match database keys
                formatted_label = label.lower().replace(' ', '_')
                detected_items.append({"label": formatted_label, "confidence": conf})

        # Group items by label and select highest confidence score
        final_items = {}
        for item in detected_items:
            label = item["label"]
            if label not in final_items or item["confidence"] > final_items[label]["confidence"]:
                # Check if the item exists in the products database
                if label in products_db[category]:
                    product_info = products_db[category][label]
                    item.update(product_info)  # Add product details from database
                    final_items[label] = item

        return list(final_items.values())
    except Exception as e:
        print(f"Error processing image: {e}")
        return []

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/category/<category>')
def category(category):
    if category not in ['fruits_vegetables', 'essentials']:
        return redirect(url_for('home'))
    products = products_db[category]
    return render_template('category.html', category=category, products=products)


@app.route('/upload/<category>', methods=['POST'])
def upload(category):
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    # Process the image with category-specific model
    image_data = image_file.read()
    detected_items = process_image(image_data, category)

    if not detected_items:
        return jsonify({'error': 'No items detected in the image'}), 400

    # Format response with product details
    response_items = []
    for item in detected_items:
        product_info = products_db.get(category, {}).get(item['label'])
        if product_info:
            response_items.append({
                'label': item['label'],
                'confidence': item['confidence'],
                'price': product_info.get('price', 0),
                'unit': product_info.get('unit', 'per piece'),
                'image': product_info.get('image', 'https://via.placeholder.com/300x200?text=Product+Image'),
                'description': product_info.get('description', item['label'].replace('_', ' ').title())
            })
        else:
            # Fallback for detected items not in database
            response_items.append({
                'label': item['label'],
                'confidence': item['confidence'],
                'price': 0,
                'unit': 'per piece',
                'image': 'https://via.placeholder.com/300x200?text=Product+Image',
                'description': item['label'].replace('_', ' ').title()
            })

    return jsonify({'items': response_items})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'email': request.form['email']})

        if existing_user is None:
            hashpass = generate_password_hash(request.form['password'])
            users.insert_one({
                'name': request.form['name'],
                'email': request.form['email'],
                'password': hashpass
            })
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        
        flash('Email already exists!', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        login_user = users.find_one({'email': request.form['email']})

        if login_user:
            if check_password_hash(login_user['password'], request.form['password']):
                session['user_id'] = str(login_user['_id'])
                session['user_name'] = login_user['name']
                flash('Logged in successfully!', 'success')
                return redirect(url_for('home'))
        
        flash('Invalid email/password combination', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/cart', methods=['GET'])
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Find the cart for the current user
    cart = mongo.db.carts.find_one({'user_id': session['user_id']})
    
    # If no cart exists, create an empty cart structure
    if not cart:
        cart = {'user_id': session['user_id'], 'items': []}
        mongo.db.carts.insert_one(cart)
    
    # Calculate cart totals
    total = 0
    for item in cart.get('items', []):
        product = products_db.get(item['category'], {}).get(item['product'])
        if product:
            item['price'] = product['price']
            item['subtotal'] = product['price'] * item['quantity']
            total += item['subtotal']
    
    return render_template('cart.html', cart=cart, products=products_db, total=total)



@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
        
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    product_id = data.get('product')
    quantity = int(data.get('quantity', 1))
    category = data.get('category')
    
    if not all([product_id, category]):
        return jsonify({'error': 'Invalid product information'}), 400
    
    # Check if product exists in the database
    if category not in products_db or product_id not in products_db[category]:
        return jsonify({'error': f'Product {product_id} not found in category {category}'}), 404
    
    # Find or create cart for the user
    cart = mongo.db.carts.find_one({'user_id': session['user_id']})
    if not cart:
        cart = {'user_id': session['user_id'], 'items': []}
    
    # Find if product already exists in cart
    cart_item = next((item for item in cart.get('items', []) 
                     if item['product'] == product_id and item['category'] == category), None)
    
    if cart_item:
        # Update existing item
        if quantity <= 0:
            cart['items'].remove(cart_item)
        else:
            cart_item['quantity'] = quantity
    else:
        # Add new item
        if quantity > 0:
            cart['items'].append({
                'product': product_id,
                'quantity': quantity,
                'category': category
            })
    
    # Update or insert cart in MongoDB
    mongo.db.carts.update_one(
        {'user_id': session['user_id']},
        {'$set': cart},
        upsert=True
    )
    
    # Calculate cart total
    cart_total = sum(item['quantity'] for item in cart['items'])
    
    return jsonify({
        'message': 'Cart updated successfully',
        'cart_total': cart_total
    })


@app.route('/cart/count')
def get_cart_count():
    if 'user_id' not in session:
        return jsonify({'cart_total': 0})
    
    cart = mongo.db.carts.find_one({'user_id': session['user_id']})
    if not cart or 'items' not in cart:
        return jsonify({'cart_total': 0})
    
    cart_total = sum(item['quantity'] for item in cart['items'])
    return jsonify({'cart_total': cart_total})

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's cart
    cart = mongo.db.carts.find_one({'user_id': session['user_id']})
    if not cart or not cart.get('items'):
        return redirect(url_for('view_cart'))
    
    if request.method == 'POST':
        # Calculate total amount
        total = 0
        items = []
        for item in cart.get('items', []):
            # CORRECTED: Access products using category and product ID
            category_products = products_db.get(item.get('category', ''), {})
            product_info = category_products.get(item.get('product', ''))
            
            if product_info:
                price = product_info['price']
                quantity = item.get('quantity', 1)
                total += price * quantity
                items.append({
                    'product': item['product'],
                    'quantity': quantity,
                    'price': price,
                    'subtotal': price * quantity,
                    'category': item.get('category')
                })
        
        # Add delivery fee and tax (rest of the code remains the same)
        delivery_fee = 40
        tax = round(total * 0.05)
        final_total = total + delivery_fee + tax
        
        # Create order
        order = {
            'user_id': session['user_id'],
            'order_items': items,
            'subtotal': total,
            'delivery_fee': delivery_fee,
            'tax': tax,
            'total': final_total,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'shipping_address': {
                'full_name': request.form.get('full_name'),
                'phone': request.form.get('phone'),
                'address_line1': request.form.get('address_line1'),
                'address_line2': request.form.get('address_line2'),
                'city': request.form.get('city'),
                'state': request.form.get('state'),
                'pincode': request.form.get('pincode')
            },
            'payment_method': request.form.get('payment_method')
        }
        
        # Save order to database
        order_id = mongo.db.orders.insert_one(order).inserted_id
        
        # Clear user's cart
        mongo.db.carts.update_one(
            {'user_id': session['user_id']},
            {'$set': {'items': []}}
        )
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=str(order_id)))
    
    return render_template('checkout.html', cart=cart, products=products_db)


from bson.errors import InvalidId

@app.route('/order-confirmation/<order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        order = mongo.db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            flash('Order not found', 'error')
            return redirect(url_for('home'))
    except InvalidId:
        flash('Invalid order ID', 'error')
        return redirect(url_for('home'))

    if order['user_id'] != session['user_id']:
        flash('You are not authorized to view this order', 'error')
        return redirect(url_for('home'))

    # Ensure each order item has valid product information
    for item in order.get('order_items', []):
        category = item.get('category', 'unknown')  # Handle missing category
        product_info = products_db.get(category, {}).get(item.get('product', ''))

        if not product_info:  # Handle missing products gracefully
            product_info = {
                'image': 'https://via.placeholder.com/300x200?text=No+Image',
                'description': item.get('product', 'Unknown').replace('_', ' ').title()
            }

        item['image'] = product_info.get('image')
        item['description'] = product_info.get('description')

    # Add cancellation timestamp if missing
    if order['status'] == 'cancelled' and 'cancelled_at' not in order:
        mongo.db.orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'cancelled_at': datetime.utcnow()}}
        )
        order = mongo.db.orders.find_one({'_id': ObjectId(order_id)})

    return render_template('order_confirmation.html', order=order, products_db=products_db)


@app.route('/orders')
def user_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        orders = list(mongo.db.orders.find({'user_id': session['user_id']}).sort('created_at', -1))
    except InvalidId:
        orders = []
    
    return render_template('orders.html', orders=orders)

@app.route('/cancel-order/<order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        order = mongo.db.orders.find_one({
            '_id': ObjectId(order_id),
            'user_id': session['user_id']
        })
    except InvalidId:
        flash('Invalid order ID', 'error')
        return redirect(url_for('user_orders'))
    
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('user_orders'))
    
    if order['status'] not in ['pending', 'processing']:
        flash('This order cannot be cancelled', 'error')
        return redirect(url_for('user_orders'))
    
    # Update order status
    mongo.db.orders.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': 'cancelled'}}
    )
    
    flash('Order cancelled successfully', 'success')
    return redirect(url_for('user_orders'))

@app.route('/chat/history')
@chat_auth_required
def get_chat_history():
    try:
        # Get last 10 messages for the user
        messages = mongo.db.chat_messages.find(
            {'user_id': session['user_id']}
        ).sort('timestamp', -1).limit(10)
        
        return jsonify({
            'messages': [{
                'content': msg['content'],
                'role': msg['role'],
                'timestamp': msg['timestamp'].isoformat()
            } for msg in messages]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/chat', methods=['GET', 'POST'])
@chat_auth_required
def chat_interface():
    if request.method == 'POST':
        try:
            user_message = request.json.get('message', '')
            if not user_message:
                return jsonify({'error': 'No message provided'}), 400
            
            # Get user context
            context = get_user_context()
            
            # Get recent chat history for context
            recent_messages = list(mongo.db.chat_messages.find(
                {'user_id': session['user_id']}
            ).sort('timestamp', -1).limit(5))
            
            # Build messages array with context
            system_context = f"""
Current user information:
- Name: {context['user_name']}
- Email: {context['user_email']}
- Number of orders: {len(context['orders'])}
- Items in cart: {context['cart_items']}

Order history:
{json.dumps(context['orders'], indent=2)}

The user is already authenticated. You have access to their complete order history above.
Please provide direct assistance without asking for verification."""

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "system",
                    "content": system_context
                }
            ]
            
            # Add recent conversation history
            for msg in reversed(recent_messages):
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # Add current user message
            messages.append({
                'role': 'user',
                'content': user_message
            })
            
            # Call Groq API
            response = requests.post(
                GROQ_API_URL,
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': GROQ_MODEL,
                    'messages': messages,
                    'temperature': 0.7,
                    'max_tokens': 1000
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json()['choices'][0]['message']['content']
                
                # Save messages to database
                timestamp = datetime.utcnow()
                mongo.db.chat_messages.insert_many([
                    {
                        'user_id': session['user_id'],
                        'content': user_message,
                        'role': 'user',
                        'timestamp': timestamp
                    },
                    {
                        'user_id': session['user_id'],
                        'content': ai_response,
                        'role': 'assistant',
                        'timestamp': timestamp
                    }
                ])
                
                return jsonify({'response': ai_response})
            else:
                print(f"API Error: {response.status_code}", response.text)
                return jsonify({'error': 'Failed to get response from AI'}), 500
                
        except Exception as e:
            print(f"Chat Error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    # GET request - render chat interface
    return render_template('chat.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)