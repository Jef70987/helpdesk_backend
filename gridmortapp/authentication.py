from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


class CookieJWTAuthentication(JWTAuthentication):
    
    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        
        if token is None:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if token is None:
            return None
        
        try:
            validated_token = self.get_validated_token(token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except (InvalidToken, TokenError):
            return None
    
    def get_validated_token(self, raw_token):
        try:
            return AccessToken(raw_token)
        except Exception:
            raise InvalidToken('Invalid token')