// frontend/assets/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('diagramForm');
    const loading = document.getElementById('loading');
    const pdfViewer = document.getElementById('pdfViewer');
    const errorMessage = document.getElementById('errorMessage');
    const fileInput = document.getElementById('file');
    const diagramType = document.getElementById('diagramType');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Reset states
        errorMessage.style.display = 'none';
        pdfViewer.style.display = 'none';
        
        const file = fileInput.files[0];
        const selectedDiagramType = diagramType.value;

        if (!file || !selectedDiagramType) {
            showError('Please select both a file and diagram type');
            return;
        }

        // Check file extension
        const validExtensions = {
            'summary':['.py', '.java', '.js'],
            'class': ['.py', '.java', '.js'],
            'flowchart': ['.py', '.java'],
            'sequence': ['.py', '.java']
        };

        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!validExtensions[selectedDiagramType].includes(fileExtension)) {
            showError(`Invalid file type for ${selectedDiagramType} diagram. Supported extensions: ${validExtensions[selectedDiagramType].join(', ')}`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('diagramType', selectedDiagramType);

        try {
            loading.style.display = 'block';
            
            const response = await fetch('http://localhost:5000/generate', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                pdfViewer.src = url;
                pdfViewer.style.display = 'block';
            } else {
                const errorText = await response.text();
                showError(`Error generating diagram: ${errorText}`);
            }
        } catch (error) {
            showError('Error connecting to server. Please ensure the backend is running.');
            console.error('Error:', error);
        } finally {
            loading.style.display = 'none';
        }
    });

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    // File input change handler to show selected filename
    fileInput.addEventListener('change', function() {
        const fileName = this.files[0]?.name || 'No file selected';
        this.nextElementSibling.textContent = fileName;
    });
});