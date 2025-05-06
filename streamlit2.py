import streamlit as st
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO
from collections import Counter

# Load YOLOv8 models
@st.cache_resource
def load_model(model_path):
    return YOLO(model_path)

# Provide the correct paths to your YOLOv8 models
model_fruits_vegetables_path = "fruits_vegetables.pt"
model_checkout_path = "retail_product.pt"

model_fruits_vegetables = load_model(model_fruits_vegetables_path)
model_checkout = load_model(model_checkout_path)

# Streamlit UI
st.title("Smart Shopping List Generator")

# Image upload
uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # Convert image to OpenCV format
    image_cv = np.array(image)
    if image_cv.shape[-1] == 4:
        image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGBA2RGB)

    # Process image through both models
    results_fruits_vegetables = model_fruits_vegetables.predict(image_cv, save=False, save_txt=False)
    results_checkout = model_checkout.predict(image_cv, save=False, save_txt=False)

    # Render results for fruits and vegetables model
    annotated_image_fruits_vegetables = results_fruits_vegetables[0].plot()  # Annotate the image
    st.image(annotated_image_fruits_vegetables, caption="Fruits and Vegetables Detected", use_column_width=True)

    # Render results for retail product checkout model
    annotated_image_checkout = results_checkout[0].plot()  # Annotate the image
    st.image(annotated_image_checkout, caption="Retail Products Detected", use_column_width=True)

    # Display labels and confidences for fruits and vegetables
    st.subheader("Fruits and Vegetables Detection Results")
    fruits_vegetables_labels = []
    for box in results_fruits_vegetables[0].boxes:
        cls = int(box.cls)
        label = model_fruits_vegetables.names[cls]
        fruits_vegetables_labels.append(label)

    # Display labels and confidences for retail products
    st.subheader("Retail Product Detection Results")
    checkout_labels = []
    for box in results_checkout[0].boxes:
        cls = int(box.cls)
        label = model_checkout.names[cls]
        checkout_labels.append(label)

    # Combine all labels
    all_labels = fruits_vegetables_labels + checkout_labels

    # Exclude unwanted detections (e.g., "cart")
    excluded_labels = {"cart"}
    filtered_labels = [label for label in all_labels if label not in excluded_labels]

    # Count occurrences of each product
    product_count = Counter(filtered_labels)

    # Display the shopping list with counts
    st.subheader("Shopping List")
    shopping_list = []
    for product, count in product_count.items():
        shopping_list.append(f"{product} {count}")
        st.write(f"{product} {count}")

    # Display a total bill estimate (optional, based on your dataset labels and price mapping)
    # Example (add product price mapping to generate total cost):
    product_prices = {
        "apple": 1.2,  # price in dollars
        "banana": 0.5,
        "carrot": 0.8,
        "corn": 1.5,  # Example product
        # Add all product names with their respective prices
    }

    total_bill = 0
    for product, count in product_count.items():
        if product.lower() in product_prices:
            total_bill += product_prices[product.lower()] * count
    
    st.subheader("Total Bill Estimate")
    st.write(f"${total_bill:.2f}")
