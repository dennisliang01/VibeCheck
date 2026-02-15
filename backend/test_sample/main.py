"""Main application entry point."""
from src.user_service import get_user, handle_request

def main():
    """Main function."""
    # No error handling
    result = handle_request({'user_id': '123'})
    print(result)

if __name__ == '__main__':
    main()
