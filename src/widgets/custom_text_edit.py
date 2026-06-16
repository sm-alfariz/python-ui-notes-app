from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QImage
from PySide6.QtCore import QBuffer, QByteArray, QIODevice

class CustomTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        """
        Override default paste behavior to handle images from clipboard.
        """
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                # Convert image to base64-encoded PNG for embedding
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                base64_data = ba.toBase64().data().decode()

                # Create HTML <img> tag with embedded base64 PNG
                html_img = f'<img src="data:image/png;base64,{base64_data}">'
                self.textCursor().insertHtml(html_img)
                return  # Skip default paste
        # Fallback to default behavior for text/other formats
        super().insertFromMimeData(source)
