import ast
import os
import logging
from dataclasses import dataclass
from typing import List, Dict
import plantuml
from datetime import datetime
import sys
import requests
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class Message:
    from_participant: str
    to_participant: str
    message: str
    sequence_number: int
    message_type: str
    description: str = ""
    file_source: str = ""

class SingleFileSequenceDiagramGenerator:
    def __init__(self, file_path: str = None):
        if file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.file_path = os.path.join(project_root, 'testing', 'python_seq', 'member.py')
        else:
            self.file_path = file_path
            
        self.messages = []
        self.participants = set()
        self.sequence_number = 1
        self.files_analyzed = set()
        
        if not os.path.exists(self.file_path):
            raise ValueError(f"File does not exist: {self.file_path}")
        
        logging.info(f"Initialized with file: {self.file_path}")

    def analyze_file(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                try:
                    tree = ast.parse(file.read())
                    self._analyze_tree(tree, self.file_path)
                    self.files_analyzed.add(self.file_path)
                    logging.info(f"Successfully analyzed: {os.path.basename(self.file_path)}")
                    return True
                except SyntaxError as e:
                    logging.error(f"Syntax error in {self.file_path}: {e}")
                    return False
        except Exception as e:
            logging.error(f"Error reading file {self.file_path}: {e}")
            return False

    def _analyze_tree(self, tree, file_path):
        class MethodVisitor(ast.NodeVisitor):
            def __init__(self, outer, source_file):
                self.outer = outer
                self.current_class = None
                self.current_method = None
                self.source_file = source_file

            def visit_ClassDef(self, node):
                self.current_class = node.name
                self.outer.participants.add(node.name)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                self.current_method = node.name
                docstring = ast.get_docstring(node)
                
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        self._analyze_call(stmt.value, docstring)
                
                self.generic_visit(node)

            def _analyze_call(self, call, docstring=""):
                if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                    from_participant = self.current_class or "System"
                    to_participant = call.func.value.id
                    message = call.func.attr
                    
                    message_type = 'dashed' if any(word in message.lower() 
                                                 for word in ['return', 'get', 'fetch', 'retrieve']) else 'solid'
                    
                    description = (f"Method '{message}' called from {from_participant} to {to_participant}\n"
                                 f"Source: {os.path.basename(self.source_file)}")
                    if docstring:
                        description += f"\nDescription: {docstring}"

                    self.outer.participants.add(to_participant)
                    self.outer.messages.append(Message(
                        from_participant=from_participant,
                        to_participant=to_participant,
                        message=f"{self.outer.sequence_number}: {message}",
                        sequence_number=self.outer.sequence_number,
                        message_type=message_type,
                        description=description,
                        file_source=self.source_file
                    ))
                    self.outer.sequence_number += 1

        visitor = MethodVisitor(self, file_path)
        visitor.visit(tree)

    def generate_plantuml(self) -> str:
        if not self.messages:
            logging.warning("No messages to generate diagram from")
            return ""

        plantuml_str = """
@startuml
!theme plain
skinparam backgroundColor white
skinparam sequenceMessageAlign center
skinparam responseMessageBelowArrow true
skinparam BoxPadding 10

skinparam participant {
    BorderColor black
    BackgroundColor white
    FontColor black
}

skinparam sequence {
    ArrowColor #28a745
    ArrowFontColor #28a745
    ArrowFontSize 12
    LifeLineBorderColor grey
    LifeLineBackgroundColor white
}

skinparam note {
    BorderColor gray
    BackgroundColor white
}
"""
        plantuml_str += "\nparticipant User\n"
        for participant in sorted(self.participants):
            if participant.lower() != 'user':
                plantuml_str += f"participant {participant}\n"

        for msg in self.messages:
            arrow = "->" if msg.message_type == 'solid' else "-->"
            plantuml_str += f"{msg.from_participant} {arrow} {msg.to_participant} : <color:#28a745>{msg.message}</color>\n"

        plantuml_str += "@enduml"
        return plantuml_str

    def _generate_diagram(self, plantuml_str: str) -> bytes:
        """Helper method to generate the diagram using PlantUML"""
        try:
            server = 'http://www.plantuml.com/plantuml/png/'
            pl = plantuml.PlantUML(url=server)
            png_data = pl.processes(plantuml_str)
            return png_data
        except Exception as e:
            logging.error(f"Error generating diagram: {e}")
            raise

    def create_header_footer(self, canvas, doc):
        """Create a minimalist header and footer with separating lines"""
        canvas.saveState()
        
        # Current script directory for logo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Header positioning
        header_top = doc.pagesize[1] - 40
        
        # Add logo
        logo_path = os.path.join(current_dir, 'logo_with_white_bg.png')
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            canvas.drawImage(logo_path, 
                            doc.leftMargin - 20,
                            header_top - 35,
                            width=40, 
                            height=40,
                            preserveAspectRatio=True)
        
        # Add DevCanvas text next to logo
        canvas.setFont('Helvetica-Bold', 14)
        canvas.setFillColor(colors.Color(0.2, 0.2, 0.2))
        canvas.drawString(doc.leftMargin + 30, 
                         header_top - 25,
                         "BITM")
        
        # Add report generation date
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.Color(0.4, 0.4, 0.4))
        date_str = datetime.now().strftime('%B %d, %Y')
        canvas.drawString(doc.width + doc.leftMargin - 120,
                         header_top - 25,
                         f"Generated: {date_str}")
        
        # Header separation line
        canvas.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
        canvas.line(doc.leftMargin - 30,
                    header_top - 45,
                    doc.width + doc.leftMargin + 30,
                    header_top - 45)
        
        # Footer separation line
        canvas.line(doc.leftMargin - 30,
                    doc.bottomMargin - 20,
                    doc.width + doc.leftMargin + 30,
                    doc.bottomMargin - 20)
        
        # Footer text
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.Color(0.4, 0.4, 0.4))
        canvas.drawString(doc.leftMargin, 
                         doc.bottomMargin - 35,
                         " © Generated by BITM")
        
        # Add page number
        page_num = canvas.getPageNumber()
        canvas.drawRightString(doc.width + doc.leftMargin,
                              doc.bottomMargin - 35,
                              f"Page {page_num}")
        
        canvas.restoreState()

    def generate_enhanced_pdf(self, output_path: str = None):
        """Generate a comprehensive PDF with sequence diagram and detailed analysis"""
        if not self.messages:
            logging.error("No messages to generate PDF from")
            return False

        if output_path is None:
            output_dir = os.path.join(os.path.dirname(self.file_path), 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'sequence_diagram_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')

        try:
            # Existing diagram generation logic
            plantuml_str = self.generate_plantuml()
            if not plantuml_str:
                return False

            diagram_path = output_path.replace('.pdf', '.png')
            os.makedirs(os.path.dirname(diagram_path), exist_ok=True)

            png_data = self._generate_diagram(plantuml_str)
            
            with open(diagram_path, 'wb') as f:
                f.write(png_data)

            # Enhanced PDF Configuration
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=110,  # Increased for header
                bottomMargin=72
            )
            
            # Create custom styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='CustomHeading1',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=20,
                textColor=colors.Color(0.2, 0.2, 0.2)
            ))
            styles.add(ParagraphStyle(
                name='CustomHeading2',
                parent=styles['Heading2'],
                fontSize=16,
                spaceBefore=15,
                spaceAfter=10,
                textColor=colors.Color(0.3, 0.3, 0.3)
            ))
            styles.add(ParagraphStyle(
                name='CustomBody',
                parent=styles['Normal'],
                fontSize=11,
                leading=14,
                spaceBefore=6,
                spaceAfter=6,
                textColor=colors.Color(0.3, 0.3, 0.3)
            ))
            
            story = []
            
            # Title
            title = Paragraph("Sequence Diagram Analysis Report", styles['CustomHeading1'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", styles['CustomHeading2']))
            summary_text = Paragraph(
                f"This report presents a detailed sequence diagram analysis for the file: {os.path.basename(self.file_path)}. "
                f"The diagram captures {len(self.messages)} interactions across {len(self.participants)} participants.",
                styles['CustomBody']
            )
            story.append(summary_text)
            story.append(Spacer(1, 20))
            
            # Sequence Diagram Section
            story.append(Paragraph("Sequence Diagram", styles['CustomHeading2']))
            diagram_intro = Paragraph(
                "The following sequence diagram illustrates the interactions between different components "
                "in the analyzed Python file.",
                styles['CustomBody']
            )
            story.append(diagram_intro)
            story.append(Spacer(1, 10))
            
            # Add diagram with KeepTogether
            diagram_elements = [
                Image(diagram_path, width=7*inch, height=7*inch),
                Spacer(1, 10),
                Paragraph("Figure 1: Sequence Diagram", styles['CustomBody'])
            ]
            story.append(KeepTogether(diagram_elements))
            story.append(PageBreak())
            
            # Detailed Interaction Analysis
            story.append(Paragraph("Detailed Interaction Analysis", styles['CustomHeading2']))
            
            for msg in self.messages:
                interaction_elements = []
                interaction_elements.append(Paragraph(f"Interaction {msg.sequence_number}", styles['CustomHeading2']))
                
                data = [
                    ["From", msg.from_participant],
                    ["To", msg.to_participant],
                    ["Message", msg.message],
                    ["Description", msg.description or "No additional description"]
                ]
                
                table = Table(data, colWidths=[1.5*inch, 4.5*inch])
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 1, colors.Color(0.8, 0.8, 0.8)),
                    ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(0.3, 0.3, 0.3)),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ]))
                
                interaction_elements.append(table)
                interaction_elements.append(Spacer(1, 15))
                
                story.append(KeepTogether(interaction_elements))
            
            # Build the PDF
            doc.build(story, onFirstPage=self.create_header_footer, onLaterPages=self.create_header_footer)
            
            # Clean up temporary diagram file
            os.remove(diagram_path)
            
            logging.info(f"Generated enhanced PDF sequence diagram: {output_path}")
            return True

        except Exception as e:
            logging.error(f"Error in generate_enhanced_pdf: {e}")
            return False

    def generate_pdf(self, output_path: str = None):
        """Backwards compatibility method"""
        return self.generate_enhanced_pdf(output_path)
    
def main():
    try:
        generator = SingleFileSequenceDiagramGenerator()
        if generator.analyze_file():
            if generator.generate_enhanced_pdf():
                logging.info("Enhanced sequence diagram generation completed successfully")
            else:
                logging.error("Failed to generate sequence diagram")
        else:
            logging.error("File analysis failed")
    except Exception as e:
        logging.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()