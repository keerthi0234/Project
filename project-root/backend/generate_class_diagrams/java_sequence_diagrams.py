import os
import re
import logging
from dataclasses import dataclass
from datetime import datetime
import glob
from typing import List, Set
import plantuml
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, 
    TableStyle, PageBreak, KeepTogether
)

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

class JavaSequenceDiagramGenerator:
    def __init__(self, directory: str = None):
        if directory is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.directory = os.path.join(project_root, 'testing', 'java')
        else:
            self.directory = directory

        self.messages: List[Message] = []
        self.participants: Set[str] = set()
        self.sequence_number = 1
        self.files_analyzed: Set[str] = set()
        
        if not os.path.exists(self.directory):
            raise ValueError(f"Directory does not exist: {self.directory}")
        
        logging.info(f"Initialized with directory: {self.directory}")

    def _extract_class_name(self, content: str) -> str:
        """Extract class name using regex."""
        match = re.search(r'class\s+(\w+)', content)
        return match.group(1) if match else None

    def _extract_method_calls(self, content: str) -> List[tuple]:
        """Extract method calls using regex patterns."""
        # Pattern to match method calls like: objectName.methodName()
        pattern = r'(\w+)\s*\.\s*(\w+)\s*\('
        
        method_calls = []
        for match in re.finditer(pattern, content):
            object_name, method_name = match.groups()
            if object_name.lower() not in ['system', 'out', 'err']:  # Skip system calls
                method_calls.append((object_name, method_name))
        
        return method_calls

    def analyze_file(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Extract class name
                class_name = self._extract_class_name(content)
                if not class_name:
                    logging.warning(f"Could not find class name in {file_path}")
                    return False

                self.participants.add(class_name)
                
                # Extract method calls
                method_calls = self._extract_method_calls(content)
                
                for object_name, method_name in method_calls:
                    self.participants.add(object_name)
                    
                    # Determine message type based on method name
                    message_type = 'dashed' if any(word in method_name.lower() 
                                                 for word in ['get', 'fetch', 'retrieve', 'return']) else 'solid'
                    
                    description = (f"Method '{method_name}' called from {class_name} to {object_name}\n"
                                 f"Source: {os.path.basename(file_path)}")
                    
                    self.messages.append(Message(
                        from_participant=class_name,
                        to_participant=object_name,
                        message=f"{self.sequence_number}: {method_name}",
                        sequence_number=self.sequence_number,
                        message_type=message_type,
                        description=description,
                        file_source=file_path
                    ))
                    self.sequence_number += 1
                
                self.files_analyzed.add(file_path)
                logging.info(f"Successfully analyzed: {os.path.basename(file_path)}")
                return True
                
        except Exception as e:
            logging.error(f"Error analyzing file {file_path}: {e}")
            return False

    def analyze_directory(self) -> bool:
        java_files = glob.glob(os.path.join(self.directory, "**/*.java"), recursive=True)
        
        if not java_files:
            logging.warning(f"No Java files found in {self.directory}")
            return False

        logging.info(f"Found {len(java_files)} Java files to analyze")
        success_count = 0
        
        for file_path in java_files:
            logging.info(f"Analyzing file: {os.path.basename(file_path)}")
            if self.analyze_file(file_path):
                success_count += 1
        
        return success_count > 0

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
    LifeLineBorderColor lightgray
    LifeLineBackgroundColor white
}
"""
        # Add participants
        for participant in sorted(self.participants):
            plantuml_str += f"participant {participant}\n"

        # Add messages
        for msg in self.messages:
            arrow = "->" if msg.message_type == 'solid' else "-->"
            plantuml_str += f"{msg.from_participant} {arrow} {msg.to_participant} : {msg.message}\n"

        plantuml_str += "@enduml"
        return plantuml_str

    def create_header_footer(self, canvas, doc):
        """Create a minimalist header and footer with separating lines"""
        canvas.saveState()
        
        # Header positioning
        header_top = doc.pagesize[1] - 40
        
        # Add logo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, 'logo_with_white_bg.png')
        if os.path.exists(logo_path):
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
                         "DevCanvas")
        
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
                         " © Generated by DevCanvas")
        
        # Add page number
        page_num = canvas.getPageNumber()
        canvas.drawRightString(doc.width + doc.leftMargin,
                              doc.bottomMargin - 35,
                              f"Page {page_num}")
        
        canvas.restoreState()

    def generate_pdf(self, output_path: str = None, sequence_png_path: str = None) -> bool:
        if not self.messages:
            logging.error("No messages to generate PDF from")
            return False

        # Set output directory relative to input directory
        if output_path is None:
            output_dir = os.path.join(self.directory, 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'sequence_diagram_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')

        try:
            # Generate PlantUML diagram
            plantuml_str = self.generate_plantuml()
            if not plantuml_str:
                return False

            # Convert to PNG using PlantUML server
            server = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/png/')
            png_data = server.processes(plantuml_str)

            # Save temporary PNG
            if sequence_png_path is None:
                sequence_png_path = output_path.replace('.pdf', '.png')
            
            with open(sequence_png_path, 'wb') as f:
                f.write(png_data)

            # Create PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72, 
                leftMargin=72,
                topMargin=110,  # Adjusted for header
                bottomMargin=72
            )

            # Define styles
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

            # Build PDF content
            story = []
            
            # Title
            title = Paragraph("Java Sequence Diagram Analysis Report", styles['CustomHeading1'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", styles['CustomHeading2']))
            summary_text = Paragraph(
                f"This report presents a comprehensive sequence diagram analysis of the Java codebase. "
                f"The analysis covers {len(self.messages)} method interactions across {len(self.files_analyzed)} files "
                f"and {len(self.participants)} participants.",
                styles['CustomBody']
            )
            story.append(summary_text)
            story.append(Spacer(1, 20))
            
            # Sequence Diagram Section
            story.append(Paragraph("Sequence Diagram", styles['CustomHeading2']))
            
            diagram_intro = Paragraph(
                "The following sequence diagram illustrates interactions between classes "
                "in the codebase using standard UML notation.",
                styles['CustomBody']
            )
            story.append(diagram_intro)
            story.append(Spacer(1, 10))
            
            # Add diagram with KeepTogether to prevent awkward breaks
            diagram_elements = [
                Image(sequence_png_path, width=7*inch, height=7*inch),
                Spacer(1, 10),
                Paragraph("Figure 1: Sequence Diagram", styles['CustomBody'])
            ]
            story.append(KeepTogether(diagram_elements))
            
            # Metrics Section
            story.append(PageBreak())
            story.append(Paragraph("Metrics and Statistics", styles['CustomHeading2']))
            
            metrics_data = [
                ['Metric', 'Value'],
                ['Total Method Interactions', str(len(self.messages))],
                ['Total Files Analyzed', str(len(self.files_analyzed))],
                ['Total Participants', str(len(self.participants))],
                ['Average Interactions per Participant', f"{len(self.messages)/len(self.participants):.1f}"],
                ['First Interaction File', os.path.basename(next(iter(self.files_analyzed)) if self.files_analyzed else 'N/A')]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[3*inch, 3*inch])
            metrics_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.Color(0.8, 0.8, 0.8)),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(0.3, 0.3, 0.3)),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('PADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(metrics_table)

            # Build the PDF
            doc.build(story, onFirstPage=self.create_header_footer, onLaterPages=self.create_header_footer)
            
            # Clean up temporary files
            if sequence_png_path != output_path.replace('.pdf', '.png'):
                os.remove(sequence_png_path)
            
            logging.info(f"Generated enhanced PDF sequence diagram: {output_path}")
            return True

        except Exception as e:
            logging.error(f"Error generating PDF: {e}")
            return False

def main():
    try:
        # Initialize with default directory structure
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        input_dir = os.path.join(project_root, 'testing', 'java')
        
        logging.info(f"Set input directory to: {input_dir}")
        
        generator = JavaSequenceDiagramGenerator(input_dir)
        if generator.analyze_directory():
            if generator.generate_pdf():
                logging.info("Sequence diagram generation completed successfully")
            else:
                logging.error("Failed to generate sequence diagram")
        else:
            logging.error("No files were analyzed successfully")
    except Exception as e:
        logging.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()