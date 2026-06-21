"""HTML rendering delegate for table cells."""

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument


class HTMLDelegate(QStyledItemDelegate):
    """Delegate to render HTML content in table cells using QTextDocument.

    This allows rich text formatting in QTableWidget cells while maintaining
    proper selection highlighting and clipping behavior.

    Usage:
        table.setItemDelegateForColumn(column_index, HTMLDelegate(table))
    """

    def paint(self, painter, option, index):
        """Render the cell with HTML content.

        Args:
            painter: The QPainter to use for rendering.
            option: Style options for the cell.
            index: Model index containing the data to display.
        """
        # Prefer UserRole+1 (snippet HTML), fall back to display text
        html_content = index.data(Qt.UserRole + 1) or index.data(Qt.DisplayRole)

        if not html_content:
            super().paint(painter, option, index)
            return

        doc = QTextDocument()
        doc.setHtml(str(html_content))

        painter.save()

        # Draw selection highlight
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Render document clipped to cell
        painter.translate(option.rect.topLeft())
        clip = option.rect.translated(-option.rect.topLeft())
        painter.setClipRect(clip)
        doc.setTextWidth(clip.width())
        doc.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index):
        """Calculate the preferred size for the cell content.

        Args:
            option: Style options for the cell.
            index: Model index containing the data to display.

        Returns:
            QSize: The preferred size for rendering the HTML content.
        """
        html_content = index.data(Qt.UserRole + 1) or index.data(Qt.DisplayRole)
        if not html_content:
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setHtml(str(html_content))
        doc.setTextWidth(option.rect.width())
        return doc.size().toSize()