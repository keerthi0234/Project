import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import google.generativeai as genai
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload and results directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Configure Google AI - You'll need to set this with your API key
GOOGLE_API_KEY = "AIzaSyAi_gXJ-dlFMX6C3nQ7LL3ww29wK0-1_3k"  # Better to use environment variable
genai.configure(api_key=GOOGLE_API_KEY)

def read_code_file(file_path):
    """Read the contents of the code file."""
    with open(file_path, 'r') as file:
        return file.read()

def generate_combined_pdf(contents, output_file):
    """Generate a PDF with combined summaries."""
    c = canvas.Canvas(output_file, pagesize=letter)
    width, height = letter
    left_margin = 72  # 1-inch margin
    right_margin = 72  # 1-inch margin
    usable_width = width - left_margin - right_margin
    text_y = height - left_margin  # Start position for text
    
    for content in contents:
        lines = content.splitlines()
        for line in lines:
            words = line.split(" ")
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if c.stringWidth(test_line, "Helvetica", 12) <= usable_width:
                    current_line = test_line
                else:
                    c.drawString(left_margin, text_y, current_line)
                    text_y -= 20
                    current_line = word
            
            if current_line:
                c.drawString(left_margin, text_y, current_line)
                text_y -= 20
            
            if text_y < left_margin:
                c.showPage()
                text_y = height - left_margin
        
        # Add a page break between summaries
        c.showPage()
    
    c.save()

def generate_file_summary(file_path):
    """Generate a summary for a single file."""
    try:
        code_content = read_code_file(file_path)
        combined_prompt = f"Summarize the code:\n\n{code_content}"
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(combined_prompt)
        
        if hasattr(response, 'text'):
            return response.text
        else:
            return f"Summary not generated for {file_path}"
    except Exception as e:
        return f"Error summarizing {file_path}: {str(e)}"

def process_directory(directory_path):
    """Process a directory and generate a combined summary PDF."""
    summaries = []
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            summary = generate_file_summary(file_path)
            summaries.append(f"File: {file_name}\n\n{summary}")
    
    output_file_name = f"summary_{os.path.basename(directory_path)}.pdf"
    output_file_path = os.path.join(app.config['RESULTS_FOLDER'], output_file_name)
    generate_combined_pdf(summaries, output_file_path)
    
    return output_file_path, output_file_name

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle directory upload and generate summary."""
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files[]')
        if not files:
            return jsonify({'error': 'No files selected'}), 400

        # Create a unique directory for this upload
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 
                                secure_filename(str(os.urandom(8).hex())))
        os.makedirs(upload_dir, exist_ok=True)

        # Save all files
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

        # Process the directory
        output_path, output_filename = process_directory(upload_dir)

        # Return the PDF file
        return send_file(output_path,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=output_filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)