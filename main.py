import streamlit as st
import cv2
import numpy as np
from sklearn.cluster import KMeans
from PIL import Image
import io

# Function to resize large images while preserving aspect ratio
def resize_image(image, max_size=1000):
    h, w = image.shape
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image

# Function to preprocess the image
def preprocess_image(image):
    # Step 1: Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    
    # Step 2: Apply histogram equalization to enhance contrast
    equalized = cv2.equalizeHist(blurred)
    
    return equalized

# Function to apply K-Means clustering for image enhancement
def enhance_image_kmeans(image, n_clusters=8):
    # Reshape image to a 1D array of pixels
    pixel_values = image.reshape(-1, 1)
    
    # Apply K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(pixel_values)
    
    # Get cluster labels and centers
    labels = kmeans.labels_
    centers = kmeans.cluster_centers_
    
    # Create segmented image by mapping pixels to cluster centers
    segmented_pixels = centers[labels].reshape(image.shape)
    segmented_image = cv2.normalize(segmented_pixels, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    return segmented_image, labels

# Function to blend original and clustered image for better detail preservation
def blend_images(original, clustered, alpha=0.7):
    # Ensure both images are in the same format
    original = original.astype(np.float32)
    clustered = clustered.astype(np.float32)
    
    # Blend: alpha * clustered + (1 - alpha) * original
    blended = alpha * clustered + (1 - alpha) * original
    blended = cv2.normalize(blended, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    return blended

# Function to apply edge enhancement
def enhance_edges(image):
    # Apply a sharpening filter to highlight edges
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(image, -1, kernel)
    return sharpened

# Streamlit app
st.title("X-ray Image Enhancement with K-Means Clustering")

# File uploader
uploaded_file = st.file_uploader("Upload an X-ray image (JPG/PNG)", type=["jpg", "png"])

# Number of clusters input
n_clusters = st.slider("Number of Clusters", min_value=2, max_value=12, value=8)

# Option to optimize for large images
optimize_large_images = st.checkbox("Optimize for Large Images (faster processing)", value=False)
if optimize_large_images:
    st.info("Images will be resized to a maximum dimension of 1000 pixels to improve performance while preserving quality.")

if uploaded_file is not None:
    # Read and display original image
    image = Image.open(uploaded_file)
    img_array = np.array(image.convert('L'))  # Convert to grayscale
    
    # Ensure img_array is uint8
    if img_array.dtype != np.uint8:
        img_array = img_array.astype(np.uint8)
    
    # Resize if optimize option is selected
    if optimize_large_images:
        img_array = resize_image(img_array, max_size=1000)
    
    # Display original image
    st.image(img_array, caption="Original X-ray Image", width=None)  # Use width=None for dynamic sizing
    # st.image(img_array, caption="Original X-ray Image", use_container_width=True)  # Fallback, commented out
    
    # Enhance image when button is clicked
    if st.button("Enhance Image"):
        with st.spinner("Enhancing image..."):
            # Preprocess image
            preprocessed_img = preprocess_image(img_array)
            
            # Ensure preprocessed_img is uint8
            if preprocessed_img.dtype != np.uint8:
                preprocessed_img = preprocessed_img.astype(np.uint8)
            
            # Display preprocessed image
            st.image(preprocessed_img, caption="Preprocessed (Contrast Enhanced)", width=None)
            # st.image(preprocessed_img, caption="Preprocessed (Contrast Enhanced)", use_container_width=True)  # Fallback
            
            # Enhance image using K-Means
            clustered_img, labels = enhance_image_kmeans(preprocessed_img, n_clusters)
            
            # Blend the clustered image with the preprocessed image
            blended_img = blend_images(preprocessed_img, clustered_img, alpha=0.7)
            
            # Apply edge enhancement
            final_img = enhance_edges(blended_img)
            
            # Ensure final_img is uint8
            if final_img.dtype != np.uint8:
                final_img = final_img.astype(np.uint8)
            
            # Display enhanced image
            st.image(final_img, caption=f"Enhanced X-ray Image ({n_clusters} Clusters)", width=None)
            # st.image(final_img, caption=f"Enhanced X-ray Image ({n_clusters} Clusters)", use_container_width=True)  # Fallback
            
            # Provide download link
            enhanced_image = Image.fromarray(final_img)
            img_byte_arr = io.BytesIO()
            enhanced_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            st.download_button(
                label="Download Enhanced Image",
                data=img_byte_arr,
                file_name="enhanced_xray.png",
                mime="image/png"
            )
else:
    st.info("Please upload an X-ray image to begin.")
