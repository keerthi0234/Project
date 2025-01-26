import os
import sys
import esprima
import pydot
import logging
import multiprocessing
from typing import Dict, List, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClassInfo:
    def __init__(self, name: str):
        self.name = name
        self.methods: List[str] = []
        self.attributes: List[str] = []
        self.base_class: str = None
        self.interfaces: List[str] = []

    def __str__(self):
        return f"ClassInfo(name={self.name}, methods={self.methods}, attributes={self.attributes}, base_class={self.base_class}, interfaces={self.interfaces})"

# Get the current script's directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Move one directory up and then set the input directory path to 'testing/javascript'
project_root = os.path.dirname(current_dir)
input_dir = os.path.join(project_root, 'testing', 'javascript')

logging.info(f"Set input directory to: {input_dir}")

def safe_write_png(graph, filename):
    output_path = os.path.join(current_dir, filename)
    try:
        graph.write_png(output_path)
        logging.info(f"Generated: {output_path}")
    except Exception as e:
        logging.error(f"Error writing {filename}: {str(e)}")
        logging.error(f"Make sure you have write permissions in {current_dir}")

def analyze_js_file(file_path: str) -> Dict[str, ClassInfo]:
    classes = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    try:
        tree = esprima.parseScript(content, {'loc': True})
    except Exception as e:
        logging.error(f"Syntax error in file: {file_path}")
        logging.error(f"Error details: {e}")
        return {}

    def visit_node(node, class_name='Global'):
        if isinstance(node, esprima.nodes.ClassDeclaration):
            class_name = node.id.name
            class_info = ClassInfo(class_name)
            
            for body_node in node.body.body:
                if isinstance(body_node, esprima.nodes.MethodDefinition):
                    class_info.methods.append(body_node.key.name)
                elif isinstance(body_node, esprima.nodes.PropertyDefinition):
                    class_info.attributes.append(body_node.key.name)
            
            if node.superClass:
                class_info.base_class = node.superClass.name
            
            classes[class_name] = class_info
        elif hasattr(node, 'body'):
            if isinstance(node.body, list):
                for child_node in node.body:
                    visit_node(child_node, class_name)
            else:
                visit_node(node.body, class_name)

    # Handle the root node (Script) separately
    if hasattr(tree, 'body') and isinstance(tree.body, list):
        for child_node in tree.body:
            visit_node(child_node)
    else:
        visit_node(tree)

    return classes

def list_js_files(directory: str) -> List[str]:
    js_files = []
    logging.info(f"Checking files in directory: {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            logging.info(f"Found file: {full_path}")
            if file.endswith('.js'):
                js_files.append(full_path)
                logging.info(f"Identified JavaScript file: {full_path}")
    return js_files

def analyze_directory(directory: str) -> Dict[str, ClassInfo]:
    all_classes = {}
    file_paths = list_js_files(directory)
    
    if not file_paths:
        logging.error(f"No JavaScript files found in directory: {directory}")
        return all_classes

    with multiprocessing.Pool() as pool:
        results = pool.map(analyze_js_file, file_paths)
        for result in results:
            all_classes.update(result)
    
    if not all_classes:
        logging.error(f"No classes found in any of the {len(file_paths)} JavaScript files analyzed.")
    else:
        logging.info(f"Found {len(all_classes)} classes in {len(file_paths)} JavaScript files.")
    
    return all_classes

def generate_class_diagram(classes: Dict[str, ClassInfo]) -> pydot.Dot:
    graph = pydot.Dot(graph_type='digraph')
    graph.set_rankdir('TB')
    graph.set_size('8.5,11')  # Set size to letter paper dimensions
    graph.set_dpi('300')  # Increase DPI for better quality

    if not classes:
        logging.warning("No classes found to generate diagram.")
        return graph

    for class_name, class_info in classes.items():
        label = f'{{{class_name}|'
        if class_info.attributes:
            label += '\\n'.join(class_info.attributes) + '|'
        label += '\\n'.join(class_info.methods) + '}'
        
        node = pydot.Node(class_name, label=label, shape='record')
        graph.add_node(node)

        if class_info.base_class:
            edge = pydot.Edge(class_info.base_class, class_name, label='extends')
            graph.add_edge(edge)

    return graph

def generate_pdf(diagram_path: str, output_path: str, classes: Dict[str, ClassInfo]):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Add title
    title = Paragraph("JavaScript Class Diagram", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Add description
    description = Paragraph("This is a UML class diagram representing the structure of the analyzed JavaScript code. "
                            "It shows classes, their attributes, methods, and relationships.", styles['Normal'])
    story.append(description)
    story.append(Spacer(1, 12))

    # Add the diagram image
    img = Image(diagram_path, width=500, height=500)
    story.append(img)
    story.append(Spacer(1, 12))

    # Add class information
    for class_name, class_info in classes.items():
        class_title = Paragraph(f"Class: {class_name}", styles['Heading2'])
        story.append(class_title)
        
        if class_info.attributes:
            attributes = Paragraph(f"Attributes: {', '.join(class_info.attributes)}", styles['Normal'])
            story.append(attributes)
        
        if class_info.methods:
            methods = Paragraph(f"Methods: {', '.join(class_info.methods)}", styles['Normal'])
            story.append(methods)
        
        if class_info.base_class:
            base_class = Paragraph(f"Base Class: {class_info.base_class}", styles['Normal'])
            story.append(base_class)
        
        story.append(Spacer(1, 12))

    doc.build(story)

def main():
    logging.info(f"Analyzing directory: {input_dir}")
    classes = analyze_directory(input_dir)
    
    if not classes:
        logging.error("No classes found in the specified directory. Please check your input directory.")
        return
    logging.info(f"Found {len(classes)} classes.")
    
    diagram = generate_class_diagram(classes)
    
    png_path = os.path.join(current_dir, 'Combined_JavaScript_Class_Diagram.png')
    safe_write_png(diagram, png_path)

    pdf_path = os.path.join(current_dir, 'JavaScript_Class_Diagram_Report.pdf')
    generate_pdf(png_path, pdf_path, classes)
    logging.info(f"PDF report generated: {pdf_path}")

if __name__ == "__main__":
    main()