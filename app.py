import io
import zipfile
import urllib.parse
import base64
import mimetypes
from flask import Flask, render_template_string, request, send_file
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Single-file approach: The HTML template is embedded directly.
# We use Tailwind CSS via CDN for styling.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Extractor</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 min-h-screen font-sans text-slate-800 pb-24">
    <div class="max-w-6xl mx-auto py-10 px-4">
        <h1 class="text-4xl font-extrabold text-center text-indigo-600 mb-8 tracking-tight">Image Extractor</h1>

        <!-- Error Message Display -->
        {% if error %}
        <div class="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded mb-8 shadow-sm">
            <p class="font-medium">Error extracting images</p>
            <p class="text-sm mt-1">{{ error }}</p>
        </div>
        {% endif %}

        <!-- STEP 1: URL Input Form -->
        {% if step == 'input' %}
        <div class="bg-white p-8 rounded-xl shadow-sm border border-slate-200 max-w-xl mx-auto">
            <form action="/extract" method="POST" class="space-y-5">
                <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-2">Website URL</label>
                    <input type="url" name="url" required placeholder="https://example.com" 
                           class="w-full border border-slate-300 rounded-lg p-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all">
                    <p class="text-xs text-slate-500 mt-2">Enter a full URL including http:// or https://</p>
                </div>
                <button type="submit" class="w-full bg-indigo-600 text-white p-3 rounded-lg font-semibold hover:bg-indigo-700 transition-colors shadow-sm">
                    Find Images
                </button>
            </form>
        </div>
        {% endif %}

        <!-- STEP 2: Results & Selection Form -->
        {% if step == 'results' %}
        <div class="mb-6 flex flex-col sm:flex-row sm:justify-between sm:items-center bg-white p-5 rounded-xl shadow-sm border border-slate-200 gap-4">
            <div>
                <h2 class="text-xl font-bold text-slate-800">Found {{ images|length }} images</h2>
                <p class="text-sm text-slate-500 truncate max-w-lg">From: <a href="{{ url }}" target="_blank" class="text-indigo-500 hover:underline">{{ url }}</a></p>
            </div>
            <a href="/" class="text-indigo-600 font-medium hover:text-indigo-800 bg-indigo-50 px-4 py-2 rounded-lg transition-colors">Scan Another URL</a>
        </div>

        <form action="/download" method="POST">
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {% for img in images %}
                <label class="cursor-pointer relative group block w-full aspect-square bg-slate-100 rounded-xl overflow-hidden border-2 border-transparent transition-all duration-200 shadow-sm hover:shadow-md" id="label-{{ loop.index }}">
                    <!-- Hidden checkbox linked to the label -->
                    <input type="checkbox" name="images" value="{{ img }}" class="hidden" onchange="toggleSelect(this, 'label-{{ loop.index }}')">
                    
                    <!-- The image itself -->
                    <img src="{{ img }}" alt="Extracted image {{ loop.index }}" class="object-contain w-full h-full p-2 group-hover:scale-105 transition-transform duration-300">
                    
                    <!-- Selection Indicator (Checkmark) -->
                    <div class="absolute top-3 right-3 bg-indigo-600 text-white rounded-full p-1 hidden check-icon shadow-lg">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
                    </div>
                </label>
                {% endfor %}
            </div>
            
            <!-- Sticky Bottom Action Bar -->
            <div class="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-4 shadow-[0_-4px_15px_-5px_rgba(0,0,0,0.1)] z-50">
                <div class="max-w-6xl mx-auto flex justify-between items-center px-4">
                    <span class="font-semibold text-slate-700" id="selection-count">0 images selected</span>
                    <div class="flex gap-3">
                        <button type="button" onclick="selectAll()" class="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">Select All</button>
                        <button type="submit" class="bg-indigo-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-indigo-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed" id="download-btn" disabled>
                            Download ZIP
                        </button>
                    </div>
                </div>
            </div>
        </form>
        
        <script>
            // UI Logic for handling image selection visual states
            function toggleSelect(checkbox, labelId) {
                const label = document.getElementById(labelId);
                const checkIcon = label.querySelector('.check-icon');
                
                if (checkbox.checked) {
                    label.classList.add('border-indigo-500', 'opacity-90');
                    label.querySelector('img').classList.add('scale-105');
                    checkIcon.classList.remove('hidden');
                } else {
                    label.classList.remove('border-indigo-500', 'opacity-90');
                    label.querySelector('img').classList.remove('scale-105');
                    checkIcon.classList.add('hidden');
                }
                updateCount();
            }

            // Select all functionality
            function selectAll() {
                const checkboxes = document.querySelectorAll('input[name="images"]');
                const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                
                checkboxes.forEach((cb, index) => {
                    if (cb.checked === allChecked) {
                        cb.checked = !allChecked;
                        toggleSelect(cb, `label-${index + 1}`);
                    }
                });
            }

            // Updates the counter and the state of the download button
            function updateCount() {
                const count = document.querySelectorAll('input[name="images"]:checked').length;
                document.getElementById('selection-count').innerText = count + ' image' + (count !== 1 ? 's' : '') + ' selected';
                const btn = document.getElementById('download-btn');
                btn.disabled = count === 0;
            }
            
            // Initial state
            updateCount();
        </script>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """Render the initial URL input form."""
    return render_template_string(HTML_TEMPLATE, step='input')

@app.route('/extract', methods=['POST'])
def extract():
    """Scrape the provided URL for image tags."""
    import re
    url = request.form.get('url')
    
    # Use a standard browser User-Agent to prevent getting blocked by basic anti-bot scripts
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')

        image_urls = set() # Using a set prevents duplicate images
        
        # Helper function to process and validate URLs
        def add_url(src):
            if not src: return
            if src.startswith('data:image'):
                image_urls.add(src)
            else:
                abs_url = urllib.parse.urljoin(url, src.strip())
                if abs_url.startswith('http'):
                    image_urls.add(abs_url)

        # 1. Find standard image tags (src, data-src, srcset)
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src', 'data-lazy-src']:
                add_url(img.get(attr))
            
            # Check srcset for responsive images
            srcset = img.get('srcset') or img.get('data-srcset')
            if srcset:
                for part in srcset.split(','):
                    add_url(part.strip().split(' ')[0])

        # 2. Find <picture> source tags
        for source in soup.find_all('source'):
            srcset = source.get('srcset') or source.get('data-srcset')
            if srcset:
                for part in srcset.split(','):
                    add_url(part.strip().split(' ')[0])

        # 3. Find Favicons and Apple Touch Icons
        for link in soup.find_all('link'):
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = [rel]
            if any('icon' in r.lower() for r in rel):
                add_url(link.get('href'))

        # 4. Find inline background images across ALL elements
        for el in soup.find_all(style=True):
            style = el.get('style', '')
            bg_matches = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style, re.IGNORECASE)
            for bg in bg_matches:
                add_url(bg)
        
        # 5. Find data-background attributes across ALL elements
        for el in soup.find_all(True):
            for attr in ['data-background', 'data-bg', 'data-background-image']:
                data_bg = el.get(attr)
                if data_bg and not data_bg.startswith('{'): # Avoid JSON payloads
                    add_url(data_bg)

        # 6. Extract inline SVGs (often used for modern logos and icons)
        for svg in soup.find_all('svg'):
            svg_str = str(svg)
            # Encode SVG safely into a base64 Data URI so the browser can preview it
            b64 = base64.b64encode(svg_str.encode('utf-8')).decode('utf-8')
            data_uri = f"data:image/svg+xml;base64,{b64}"
            image_urls.add(data_uri)

        return render_template_string(HTML_TEMPLATE, step='results', images=list(image_urls), url=url)
    
    except Exception as e:
        # If the URL is invalid or blocked, return to step 1 with the error
        return render_template_string(HTML_TEMPLATE, step='input', error=str(e))

@app.route('/download', methods=['POST'])
def download():
    """Download selected images on the backend, zip them, and send to the user."""
    selected_urls = request.form.getlist('images')
    if not selected_urls:
        return "No images selected", 400

    # Create an in-memory byte buffer to store the ZIP file
    memory_file = io.BytesIO()
    
    # Create the zipfile
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for i, img_url in enumerate(selected_urls):
            try:
                if img_url.startswith('data:image/'):
                    # Handle inline SVGs and base64 encoded images
                    header, encoded = img_url.split(',', 1)
                    ext = '.png' # fallback
                    if 'svg+xml' in header: ext = '.svg'
                    elif 'jpeg' in header or 'jpg' in header: ext = '.jpg'
                    elif 'gif' in header: ext = '.gif'
                    
                    file_data = base64.b64decode(encoded)
                    filename = f"inline_asset_{i}{ext}"
                    zf.writestr(f"{i + 1}_{filename}", file_data)
                else:
                    # Fetch standard external image URLs
                    r = requests.get(img_url, stream=True, timeout=5)
                    if r.status_code == 200:
                        # Parse URL and safely remove query params to get a clean filename
                        parsed = urllib.parse.urlparse(img_url)
                        clean_path = urllib.parse.unquote(parsed.path)
                        filename = clean_path.split('/')[-1]
                        
                        # Fallback if URL doesn't end in a standard file name
                        if not filename or '.' not in filename:
                            content_type = r.headers.get('content-type', '')
                            ext = mimetypes.guess_extension(content_type.split(';')[0]) or '.jpg'
                            filename = f'image_{i}{ext}'

                        # Ensure unique filenames in the zip to avoid overwriting
                        unique_filename = f"{i + 1}_{filename}"
                        
                        # Write the raw image bytes into the zip file
                        zf.writestr(unique_filename, r.content)
            except Exception as e:
                # If a single image fails, skip it and continue packing the rest
                print(f"Skipping asset due to error: {e}")

    # Rewind the buffer to the beginning so it can be read and sent
    memory_file.seek(0)
    
    return send_file(
        memory_file, 
        download_name='extracted_images.zip', 
        as_attachment=True,
        mimetype='application/zip'
    )

if __name__ == '__main__':
    # Run the application locally
    app.run(debug=True, port=5000)