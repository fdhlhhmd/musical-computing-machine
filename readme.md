## Image Extractor App

This is a lightweight Python web application that extracts images from any given webpage URL, displays them in a modern grid interface, and allows you to download your selections as a single .zip file.

<img width="1153" height="949" alt="image" src="https://github.com/user-attachments/assets/3df8ac59-c487-48d9-9317-112827da0c06" />

## Prerequisites

Ensure you have Python 3.8+ installed on your computer.

### Setup Instructions

Install Dependencies
Open your terminal/command prompt in the folder containing these files and run:

```
pip install -r requirements.txt
```

Run the Application
Start the Flask server by running:
```
python app.py
```

Access the App
Open your web browser and navigate to:
http://127.0.0.1:5000

## How it Works
* BeautifulSoup4 & Regex handles scraping the provided URL. The app is equipped to extract images from:
  - Standard <img> tags (src, data-src, data-lazy-src).
  - Interactive Sliders / Carousels: Automatically parses elements like swiper-slide-image by looking for inline background-image styles and data-background attributes used by modern slider libraries (like SwiperJS).
  - Automatically converts relative URL paths to full absolute links.
 
* Tailwind CSS drives the user interface without needing external stylesheets.
  
* The backend downloads your chosen files simultaneously into an in-memory ZIP archive (io.BytesIO()), avoiding the need to clutter your local hard drive with temporary downloaded files.
  
