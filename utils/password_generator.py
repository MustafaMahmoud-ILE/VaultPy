import secrets
import string

class PasswordGenerator:
    """Secure password generator using the secrets module."""

    @staticmethod
    def generate(length=16, use_upper=True, use_lower=True, use_digits=True, use_symbols=True) -> str:
        """Generates a secure password based on specified constraints."""
        if length < 4:
            length = 4  # Minimum length to satisfy all categories

        categories = []
        if use_upper: categories.append(string.ascii_uppercase)
        if use_lower: categories.append(string.ascii_lowercase)
        if use_digits: categories.append(string.digits)
        if use_symbols: categories.append(string.punctuation)

        if not categories:
            return ""

        # Ensure at least one character from each selected category
        password = [secrets.choice(cat) for cat in categories]

        # Fill the rest of the password length
        all_chars = "".join(categories)
        password += [secrets.choice(all_chars) for _ in range(length - len(categories))]

        # Shuffle the result
        secrets.SystemRandom().shuffle(password)
        return "".join(password)
