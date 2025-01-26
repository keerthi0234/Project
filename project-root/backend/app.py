# backend/app.py
import io
import logging
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import sys
import importlib
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Image
from werkzeug.utils import secure_filename
from generate_class_diagrams.combined_pyclass_diagrams import (
    analyze_directory,
    generate_class_diagram,
    safe_write_png,
    generate_enhanced_pdf)

from generate_class_diagrams.python_sequence import SingleFileSequenceDiagramGenerator
from generate_class_diagrams.python_flowcharts import (
    analyze_python_file,
    generate_flowcharts, 
    generate_pdf,
    safe_write_png
)
from generate_class_diagrams.python_summary import generate_file_summary
from dotenv import load_dotenv
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
app = Flask(__name__)
CORS(app)

# Add the diagram generation modules to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'generate_class_diagrams'))
# Import diagram generation modules
try:
    import combined_java_class_diagrams
    import combined_pyclass_diagrams
    import java_flowcharts
    import javascript_class_diagrams
    import java_sequence_diagrams
    import python_flowcharts
except ImportError as e:
    print(f"Error importing diagram modules: {e}")
    sys.exit(1)

def is_valid_file(filename, diagram_type):
    """Validate file extension based on diagram type."""
    valid_extensions = {
        'class': ('.py', '.java', '.js'),
        'flowchart': ('.py', '.java'),
        'sequence': ('.py', '.java'),
        'summary': ('.py', '.java', '.js', '.txt', '.md')
    }
    return filename.lower().endswith(valid_extensions.get(diagram_type, ()))

@app.route('/generate', methods=['POST'])
def generate_diagram():
    temp_dir = None
    try:
        if 'file' not in request.files:
            return 'No file provided', 400
        
        file = request.files['file']
        diagram_type = request.form.get('diagramType')
        
        if not file or not diagram_type:
            return 'Missing required fields', 400
        
        filename = secure_filename(file.filename)
        
        if not is_valid_file(filename, diagram_type):
            return f'Invalid file type for {diagram_type} diagram', 400
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        output_path = os.path.join(temp_dir, 'output.pdf')
        
        # Save uploaded file
        file.save(file_path)
        
        # Analyze directory after saving the file
        classes = analyze_directory(file_path)
        
        # Generate diagram based on type and file extension
        if diagram_type == 'summary':
            try:
                # Initialize Google AI with your API key
                import google.generativeai as genai
                genai.configure(api_key='AIzaSyAi_gXJ-dlFMX6C3nQ7LL3ww29wK0-1_3k')  # Replace with your actual API key
                
                # Read and process the file
                with open(file_path, 'r') as f:
                    code_content = f.read()
                
                # Generate summary using the AI model
                model = genai.GenerativeModel("gemini-1.5-flash")
                combined_prompt = f"Summarize the code:\n\n{code_content}"
                response = model.generate_content(combined_prompt)
                
                if not hasattr(response, 'text'):
                    return 'Failed to generate summary', 500
                    
                summary = response.text
                
                # Generate PDF with the summary
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                
                c = canvas.Canvas(output_path, pagesize=letter)
                width, height = letter
                left_margin = 72  # 1-inch margin
                text_y = height - left_margin
                
                # Add file name
                c.drawString(left_margin, text_y, f"File: {filename}")
                text_y -= 30
                
                # Add summary content
                lines = summary.splitlines()
                for line in lines:
                    words = line.split(" ")
                    current_line = ""
                    
                    for word in words:
                        test_line = f"{current_line} {word}".strip()
                        if c.stringWidth(test_line, "Helvetica", 12) <= width - 2*left_margin:
                            current_line = test_line
                        else:
                            c.drawString(left_margin, text_y, current_line)
                            text_y -= 20
                            current_line = word
                    
                    if current_line:
                        c.drawString(left_margin, text_y, current_line)
                        text_y -= 20
                
                c.save()
                
            except Exception as e:
                logging.error(f"Error generating summary: {str(e)}")
                return f'Error generating summary: {str(e)}', 500
        if diagram_type == 'class':
            if filename.endswith('.py'):
                from combined_pyclass_diagrams import analyze_file, generate_class_diagram, safe_write_png, generate_enhanced_pdf
                
                # Analyze the Python file to extract classes
                classes = analyze_file(file_path)
                
                if not classes:
                    print(f"No classes found in {file_path}. PDF report cannot be generated.")
                else:
                    # Generate the class diagram
                    diagram = generate_class_diagram(classes)
                    
                    # Save the diagram as a PNG
                    diagram_path = file_path.replace('.py', '_Class_Diagram.png')
                    safe_write_png(diagram, diagram_path)
                    
                    # Generate the PDF report
                    output_path = file_path.replace('.py', '_Class_Diagram_Report.pdf')
                    generate_enhanced_pdf(diagram_path, output_path, classes)
                    print(f"PDF report generated: {output_path}")
            elif filename.endswith('.java'):
                # Use combined_java_class_diagrams to generate the diagram for Java files
                from combined_java_class_diagrams import analyze_java_file, generate_class_diagram, safe_write_png, generate_enhanced_pdf

                # Analyze the Java file
                classes = analyze_java_file(file_path)
                
                if not classes:
                    print(f"No classes found in {file_path}. PDF report cannot be generated.")
                else:
                    # Generate the class diagram
                    diagram = generate_class_diagram(classes)
                    
                    # Save the diagram as a PNG
                    diagram_path = file_path.replace('.java', '_Class_Diagram.png')
                    safe_write_png(diagram, diagram_path)
                    
                    # Generate the PDF report
                    output_path = file_path.replace('.java', '_Class_Diagram_Report.pdf')
                    generate_enhanced_pdf(diagram_path, output_path, classes)
                    print(f"PDF report generated: {output_path}")

            elif filename.endswith('.js'):
                javascript_class_diagrams.generate(file_path, output_path)
        def check_graphviz():
            """Check if Graphviz is installed and in PATH"""
            import shutil
            return shutil.which('dot') is not None
        if not check_graphviz():
            return 'Graphviz is not installed. Please install Graphviz to generate flowcharts.', 400

        elif diagram_type == 'flowchart':
            if filename.endswith('.py'):
                try:
                    # Analyze the Python file
                    elements = analyze_python_file(file_path)
                    
                    if not elements:
                        return 'No functions or classes found to analyze', 400
                        
                    # Generate flowcharts
                    flowcharts = generate_flowcharts(elements)
                    
                    # First, ensure all PNGs are written to temp directory
                    png_files = {}  # Store PNG paths for later use
                    
                    for name, item in flowcharts.items():
                        if isinstance(item, dict):  # Class
                            png_files[name] = {}
                            for method_name, flowchart in item.items():
                                png_path = os.path.join(temp_dir, f"{name}_{method_name}_flowchart.png")
                                flowchart.write_png(png_path)
                                png_files[name][method_name] = png_path
                        else:  # Function
                            png_path = os.path.join(temp_dir, f"{name}_flowchart.png")
                            item.write_png(png_path)
                            png_files[name] = png_path
                    
                    # Now override current_dir and generate PDF
                    import generate_class_diagrams.python_flowcharts as pyflow
                    original_dir = pyflow.current_dir
                    pyflow.current_dir = temp_dir
                    
                    # Generate the PDF with the flowcharts
                    generate_pdf(flowcharts, elements, output_path)
                    
                    # Restore the original directory
                    pyflow.current_dir = original_dir
                    
                except Exception as e:
                    logging.error(f"Error in flowchart generation: {str(e)}")
                    return f'Error generating flowchart: {str(e)}', 500
                    
            elif filename.endswith('.java'):
                java_flowcharts.generate(file_path, output_path)
                    
        
        elif diagram_type == 'sequence':
            if filename.endswith('.py'):
                generator = SingleFileSequenceDiagramGenerator(file_path)
                if not generator.analyze_file():
                    return 'Error analyzing Python file', 500
                if not generator.generate_enhanced_pdf(output_path):
                    return 'Error generating sequence diagram', 500
            elif filename.endswith('.java'):
                java_sequence_diagrams.generate(file_path, output_path)
        
        # Check if output file was created
        if not os.path.exists(output_path):
            return 'Error generating diagram', 500
        
        # Read the PDF file into memory before sending
        with open(output_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Send the PDF from memory
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='diagram.pdf'
        )

    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        return f'Error processing file: {str(e)}', 500
    except Exception as e:
        # Clean up temp directory if it exists
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)