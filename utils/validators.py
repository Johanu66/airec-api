import re
from email_validator import validate_email, EmailNotValidError


def validate_email_format(email):
    """Validate email format"""
    try:
        valid = validate_email(email)
        return True, valid.email
    except EmailNotValidError as e:
        return False, str(e)


def validate_password_strength(password):
    """Validate password strength
    - At least 8 characters
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"


def validate_rating(rating):
    """Validate rating value (0.5 to 5.0 in 0.5 increments)"""
    if not isinstance(rating, (int, float)):
        return False, "Rating must be a number"
    
    if rating < 0.5 or rating > 5.0:
        return False, "Rating must be between 0.5 and 5.0"
    
    # Check if rating is in 0.5 increments
    if (rating * 2) % 1 != 0:
        return False, "Rating must be in 0.5 increments"
    
    return True, "Rating is valid"


def validate_pagination(page, per_page, max_per_page=100):
    """Validate pagination parameters"""
    try:
        page = int(page)
        per_page = int(per_page)
    except (ValueError, TypeError):
        return False, "Page and per_page must be integers", None, None
    
    if page < 1:
        return False, "Page must be greater than 0", None, None
    
    if per_page < 1:
        return False, "Per_page must be greater than 0", None, None
    
    if per_page > max_per_page:
        per_page = max_per_page
    
    return True, "Pagination is valid", page, per_page


def sanitize_string(text, max_length=None):
    """Sanitize string input"""
    if not isinstance(text, str):
        return ""
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_year(year):
    """Validate year value"""
    try:
        year = int(year)
        if year < 1800 or year > 2100:
            return False, "Year must be between 1800 and 2100"
        return True, year
    except (ValueError, TypeError):
        return False, "Year must be a valid integer"
