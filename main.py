import streamlit as st
import cv2
import numpy as np
from sklearn.cluster import KMeans
from PIL import Image
import io
import zipfile
import os
import base64

st.set_page_config(page_title="Spinal Cord Image Clustering", layout="wide")

# Custom CSS for gradient sidebar background and download button color
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #007BFF 0%, #6BCBFF 100%) !important;
    }
    .stDownloadButton > button {
        background-color: #007BFF !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: block !important;
        max-width: 350px !important;
        width: 100% !important;
        transition: background 0.2s;
    }
    .stDownloadButton > button:hover {
        background-color: #0056b3 !important;
        color: #fff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to check font availability
def check_fonts():
    try:
        test_img = np.zeros((100,100,3), dtype=np.uint8)
        cv2.putText(test_img, "Test", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        return True
    except:
        return False

# Initialize font availability
FONT_AVAILABLE = check_fonts()

# Function to resize large images
def resize_image(image, max_size=1000):
    h, w = image.shape
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image

# CLAHE preprocessing
def preprocess_image(image):
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(image)

# K-Means enhancement
def enhance_image_kmeans(image, n_clusters=8):
    pixel_values = image.reshape(-1, 1)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(pixel_values)
    labels = kmeans.labels_
    centers = kmeans.cluster_centers_
    segmented_pixels = centers[labels].reshape(image.shape)
    return cv2.normalize(segmented_pixels, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

# Image blending
def blend_images(original, clustered, alpha=0.7):
    original = original.astype(np.float32)
    clustered = clustered.astype(np.float32)
    blended = alpha * clustered + (1 - alpha) * original
    return cv2.normalize(blended, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

# Function to convert image array to raw PNG bytes
def image_to_bytes(image_array):
    # Ensure the image is in uint8 format
    if image_array.dtype != np.uint8:
        image_array = cv2.normalize(image_array, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Convert to PIL Image and save to PNG bytes
    img = Image.fromarray(image_array)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

# Function to convert image array to base64 string for display (if needed)
def image_to_base64(image_array):
    img_bytes = image_to_bytes(image_array)
    return base64.b64encode(img_bytes).decode('utf-8')

# Track which image is clicked for full view
if "full_image" not in st.session_state:
    st.session_state.full_image = None
if "full_image_caption" not in st.session_state:
    st.session_state.full_image_caption = None

# Show full image in the center if set
if st.session_state.full_image is not None:
    st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 60vh;">
    """, unsafe_allow_html=True)
    st.image(st.session_state.full_image, use_column_width=False, caption=st.session_state.full_image_caption)
    st.markdown("""
        </div>
    """, unsafe_allow_html=True)
    if st.button("Close Full Image", key="close_full_image", help="Close the full image view"):
        st.session_state.full_image = None
        st.session_state.full_image_caption = None
    st.markdown("---")

# Streamlit UI
st.sidebar.header("Spinal Cord Image Clustering")
uploaded_file = st.sidebar.file_uploader("Upload spine image", type=["jpg","png","jpeg"])
show_team = st.sidebar.checkbox("Show Team Info")

# Layout: main content (left), team info (right if checked)
if show_team:
    main_col, team_col = st.columns([3, 1])
else:
    main_col = st.container()
    team_col = None

with main_col:
    st.title("Spinal Cord Image Clustering and Analysis")

    if uploaded_file:
        # Keep original image for display
        original_image = Image.open(uploaded_file)         # Do NOT convert to grayscale here
        original_array = np.array(original_image)

        # Convert to grayscale for processing
        gray_image = original_image.convert('L')
        img_array = np.array(gray_image)

        
        filename = os.path.splitext(uploaded_file.name)[0]
        
        # Processing pipeline
        processed = preprocess_image(img_array)
        clustered = enhance_image_kmeans(processed, 8)
        enhanced = blend_images(processed, clustered)
        
        # Prepare images for download
        images_dict = {
            'Original': img_array,
            'Preprocessed': processed,
            'Clustered': clustered,
            'Enhanced': enhanced
        }
        
        # Prepare ZIP for download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for key, img_array in images_dict.items():
                img_bytes = image_to_bytes(img_array)  # Get raw PNG bytes
                zip_file.writestr(f"{filename}_{key.lower()}.png", img_bytes)
        zip_buffer.seek(0)
        
        # Display images: Original, Preprocessed, Clustered, Enhanced
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.image(original_array, caption="Original", use_column_width=True)
        with col2:
            st.image(processed, caption="Preprocessed (CLAHE)", use_column_width=True)
        with col3:
            st.image(clustered, caption="Clustered (K-Means)", use_column_width=True)
        with col4:
            st.image(enhanced, caption="Enhanced (Blended)", use_column_width=True)

        # Download buttons under each image
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.download_button(
                label="Download Original Image",
                data=image_to_bytes(img_array),
                file_name=f"{filename}_original.png",
                mime="image/png",
                key="download1"
            )
        with col2:
            st.download_button(
                label="Download Preprocessed Image",
                data=image_to_bytes(processed),
                file_name=f"{filename}_preprocessed.png",
                mime="image/png",
                key="download2"
            )
        with col3:
            st.download_button(
                label="Download Clustered Image",
                data=image_to_bytes(clustered),
                file_name=f"{filename}_clustered.png",
                mime="image/png",
                key="download3"
            )
        with col4:
            st.download_button(
                label="Download Enhanced Image",
                data=image_to_bytes(enhanced),
                file_name=f"{filename}_enhanced.png",
                mime="image/png",
                key="download4"
            )

        # Download all images as ZIP
        st.download_button(
            label="Download All Images as ZIP",
            data=zip_buffer,
            file_name=f"{filename}_images.zip",
            mime="application/zip",
            key="download_zip"
        )

    else:
        st.info("Please upload a spinal X-ray image to begin analysis")

if show_team and team_col is not None:
    with team_col:
        st.markdown("---")
        st.header("Meet the Team")
        team = [
            {
                "name": "Alice Smith",
                "role": "Lead Developer",
                "img": "https://randomuser.me/api/portraits/women/44.jpg",
                "bio": "Expert in medical imaging and AI."
            },
            {
                "name": "Bob Lee",
                "role": "Backend Engineer",
                "img": "https://randomuser.me/api/portraits/men/32.jpg",
                "bio": "Loves Python, FastAPI, and scalable systems."
            },
            {
                "name": "Carol Tan",
                "role": "UI/UX Designer",
                "img": "https://randomuser.me/api/portraits/women/68.jpg",
                "bio": "Passionate about beautiful, accessible design."
            }
        ]
        for member in team:
            st.image(member["img"], width=100)
            st.subheader(member["name"])
            st.caption(member["role"])
            st.write(member["bio"])
