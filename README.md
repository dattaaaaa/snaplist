# SnapList: Object Detection and Retail Shopping Application

SnapList is an innovative web application that uses computer vision to identify fruits, vegetables, and retail products from images. It offers a complete shopping experience with user authentication, product catalog, shopping cart functionality, and order management.

![SnapList App](https://via.placeholder.com/800x400?text=SnapList+App)

## ✨ Features

- **AI-Powered Object Detection**: Upload images of fruits, vegetables, or retail products and get instant identification
- **Smart Shopping**: Add detected items directly to your cart
- **User Accounts**: Register, login, and track your order history
- **Shopping Cart**: Easily manage your items and proceed to checkout
- **Order Management**: View, track, and cancel orders
- **Intelligent Chat Assistant**: Get help with your shopping and orders through our integrated AI assistant

## 🛒 Product Categories

- **Fruits & Vegetables**: Fresh produce including apples, bananas, tomatoes, and more
- **Essentials**: Healthcare items, personal care products, and beverages

## 🔧 Technical Implementation

- **Backend**: Flask web framework with MongoDB database
- **Computer Vision**: YOLO (You Only Look Once) object detection models
- **AI Chat**: Integration with LLM for intelligent customer support
- **Authentication**: Secure user authentication with password hashing

## 📁 Project Structure

```
snaplist/
├── app.py               # Main Flask application
├── templates/           # HTML templates
├── static/              # CSS, JavaScript, and images
├── fruits_vegetables.pt # YOLO model for fruits and vegetables
├── retail_product.pt    # YOLO model for retail products
└── requirements.txt     # Python dependencies
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- MongoDB
- Groq API Key (for chat functionality)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dattaaaaa/snaplist.git
   cd snaplist
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MongoDB**
   - Install and start MongoDB on your system
   - The application will connect to `mongodb://localhost:27017/snaplist` by default

5. **Configure API Keys**
   - Replace `YOUR_API_KEY_HERE` in app.py with your Groq API key

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Open your browser and go to `http://localhost:5000`

## 📱 How to Use

1. **Register** a new account or login with existing credentials
2. **Browse** product categories or use the camera to detect items
3. **Upload** images of fruits, vegetables, or retail products
4. **Add** detected items to your cart
5. **Checkout** and complete your order
6. **Track** your order status in the orders section
7. **Chat** with the AI assistant for help with orders or product information

## 🤖 AI Features

### Image Detection
- Upload photos of fruits, vegetables, or retail products
- AI identifies items with confidence scores
- View product information and prices
- Add detected items directly to cart

### Smart Assistant
- Ask about order status
- Get product recommendations
- Receive help with app features
- Process order cancellations (within 24 hours)

## 🔒 Security Features

- Password hashing with Werkzeug
- Session-based authentication
- Order verification to prevent unauthorized access

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.


## 🙏 Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [MongoDB](https://www.mongodb.com/)
- [YOLO](https://github.com/ultralytics/ultralytics)
- [Groq](https://groq.com/)