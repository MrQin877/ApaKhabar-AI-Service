import fitz


class PDFExtractor:

    @staticmethod
    def extract(file_path: str):

        document = fitz.open(file_path)

        # ✅ MUST get page count BEFORE closing
        page_count = document.page_count

        text = ""

        for page in document:
            text += page.get_text()

        document.close()

        return {
            "pages": page_count,
            "content": text
        }