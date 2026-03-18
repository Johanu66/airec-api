"""Rebuild Chroma RAG index from the real API database."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from services.rag_service import rag_service


def main():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    with app.app_context():
        result = rag_service.rebuild_index()
        print(result)


if __name__ == '__main__':
    main()
