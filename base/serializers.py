import os
from dotenv import load_dotenv
import secrets, string
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
from rest_framework import serializers
from .models import Favorite, Listing, Offer, PasswordResetToken, UserProfile, UserVerification, UserApplication, ChatMessage, ChatRoom, Listing, Wallet
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator    
from django.contrib.sites.shortcuts import get_current_site

load_dotenv()
UserModel = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    
    class Meta:
        model = UserModel
        fields = ['id', 'email', 'password', 'is_staff', 'is_reviewer', 'is_assumee', 'is_assumptor']

    def create(self, validated_data):
        if not validated_data['is_staff'] or validated_data['is_reviewer']:
            try:
                email_verified_user =  UserVerification.objects.get(user_verification_email=validated_data['email'], user_verification_is_verified=True)
            except UserVerification.DoesNotExist:
                raise serializers.ValidationError('Email has not been verified yet.')
                
        user_obj = UserModel.objects.create_user(email=validated_data['email'], password=validated_data['password'])
        user_obj.is_staff = validated_data['is_staff']
        user_obj.is_assumee = validated_data['is_assumee']
        user_obj.is_assumptor = validated_data['is_assumptor']
        user_obj.is_reviewer = validated_data['is_reviewer']
        user_obj.save()

        if not validated_data['is_staff'] or validated_data['is_reviewer']:
            email_verified_user.user_id = user_obj
            email_verified_user.save()

        return user_obj
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        instance.is_staff = validated_data.get('is_staff', instance.is_staff)
        instance.is_assumee = validated_data.get('is_assumee', instance.is_assumee)
        instance.is_assumptor = validated_data.get('is_assumptor', instance.is_assumptor)
        instance.is_reviewer = validated_data.get('is_reviewer', instance.is_reviewer)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()

        return instance
    
class AdminRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    firstname = serializers.CharField(source='first_name')
    lastname = serializers.CharField(source='last_name')
    gender = serializers.CharField()
    dob = serializers.DateField()
    phone_number = serializers.CharField(source='contact')
    address = serializers.CharField()
    # imagefile = serializers.ImageField(required=False)
    
    def generate_password(self, length=12):
        """Generate a secure random password."""
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(characters) for i in range(length))
        return password
    
    def create(self, validated_data):
        email = validated_data['email']
        password = self.generate_password()

        try: 
            admin_acc = UserModel.objects.create(email=email, is_staff=True, is_active=True)
            admin_acc.set_password(password)
            admin_acc.save()

            admin_profile = UserProfile.objects.create(user_prof_fname=validated_data['first_name'], user_prof_lname=validated_data['last_name'], 
                                                    user_prof_gender=validated_data['gender'], user_prof_dob=validated_data['dob'],
                                                    user_prof_mobile=validated_data['contact'], user_prof_address=validated_data['address'], user_id=admin_acc)
            
            return admin_acc, admin_profile
        except IntegrityError:
            raise serializers.ValidationError({'message': 'User with this email already exist'})
        except Exception as e:
            raise serializers.ValidationError({'message' :str(e)})


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['user_prof_id', 'user_prof_lname', 'user_prof_fname', 'user_prof_gender', 
                  'user_prof_dob', 'user_prof_mobile', 'user_prof_address', 'user_prof_valid_id', 'user_prof_pic', 'user_id']
        read_only_fields = ['user_prof_valid_id', 'user_prof_pic']

    def create(self, validated_data):
        user = super().create(validated_data)

        UserApplication.objects.create(user_prof_id=user)

        return user
    
    def update(self, instance, validated_data):
        instance.user_prof_fname = validated_data.get('user_prof_fname', instance.user_prof_fname)
        instance.user_prof_lname = validated_data.get('user_prof_lname', instance.user_prof_lname)
        instance.user_prof_gender = validated_data.get('user_prof_gender', instance.user_prof_gender)
        instance.user_prof_dob = validated_data.get('user_prof_dob', instance.user_prof_dob)
        instance.user_prof_mobile = validated_data.get('user_prof_mobile', instance.user_prof_mobile)
        instance.user_prof_address = validated_data.get('user_prof_address', instance.user_prof_address)
        instance.save()

        return instance

# class UserAccountSerializer(serializers.Serializer):
#     class Meta:
#         model = UserModel
#         fields = '__all__'

class CheckUserVerifiedSerializer(serializers.Serializer):
    user_verification_email = serializers.EmailField()

    def check_verification_status(self):
        email = self.validated_data.get('user_verification_email')
        user_verification = get_object_or_404(UserVerification, user_verification_email=email)

        return user_verification.user_verification_is_verified, user_verification.user_id
    
class EmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = ['user_verification_email', 'user_verification_code']
    
    def create(self, validated_data):
        email = validated_data['user_verification_email']
        
        return UserVerification.objects.create(user_verification_email=email, 
                                                            user_verification_expires_at=timezone.now() + timedelta(hours=24))
    
    def check_email(self, email):
        if UserModel.objects.filter(email=email).exists():
            raise serializers.ValidationError('User with this email already exists.')
        
        verification_record = UserVerification.objects.filter(user_verification_email=email, user_verification_is_verified=False).first()
        if verification_record:
            return verification_record
    
    def send_verification_email(self, request, email, verification_code):

        verification_key = f'http://192.168.1.9:8000/api/email-verify/{verification_code}/'
        html_msg = f"""
        <html>
        <body>
            <h2>Welcome  to register ASSUMATE ! Please confirm !</h2>
            <p>You are about to register to ASSUMATE account with {email}. Please click the 'Activate now' to verify your email address.</p>
            <a href="{verification_key}" style="
                display: inline-block;
                padding: 10px 20px;
                font-size: 16px;
                color: #ffffff;
                background-color: #4A8AF0;
                text-decoration: none;
                border-radius: 5px;
                text-align: center;
            ">Activate now</a>
            <p>If the button does not respond, please verify your email using the link below:</p></br>
            <p><a href="{verification_key}">{verification_key}</a></p></br>
            <p>For security reasons, the link will be only valid for 24 hours. After 24 hours, 
            you will need to register again. Thank you for supporting ASSUMATE</p>
            <p>If this is not you, please ignore this message.</p>
        </body>
        </html>"""

        email_message = EmailMessage(
        subject='ASSUMATE Account - Email address verification',
        body=html_msg,
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
            )
        
        email_message.content_subtype = "html"

        email_message.send(fail_silently=False)

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def check_user(self, validated_data):
        user = authenticate(username=validated_data['email'], password=validated_data['password'])
        if not user:
            raise serializers.ValidationError({'error': 'Incorrect email or password'})
        
        return user
    
    def to_representation(self, instance):
        user = self.check_user(self.validated_data)
        return {
            'email': user.email,
            'is_reviewer': user.is_reviewer,
            'is_assumee': user.is_assumee,
            'is_assumptor': user.is_assumptor
        }
    
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    class Meta:
        model = PasswordResetToken
        read_only_fields = ['reset_token', 'user', 'reset_token_expires_at', 'reset_token_created_at']
        # read_only_fields = ['reset_token', 'reset_token_expires_at', 'reset_token_created_at']
    
    def check_user(self, _email):
        try:
            user = UserModel.objects.get(email=_email)
            return user
        except UserModel.DoesNotExist:
            raise serializers.ValidationError('User not found.')
        
    def verify_token(self):
        return
    
    def create_token(self, email):
        user = self.check_user(email)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        expires_at =timezone.now() + timedelta(hours=1)

        reset_token, created = PasswordResetToken.objects.update_or_create(
            user=user,
            defaults={
                'reset_token': token,
                'reset_token_expires_at': expires_at,
                'reset_token_created_at': timezone.now()
            }
        )

        return user.profile.user_prof_fname, uidb64, reset_token.reset_token

    def send_reset_link(self, email):
        base_url = os.getenv('API_URL')
        template_name  = 'base/reset_link_template.html'
        name, uidb64, token = self.create_token(email)
        reset_link = f'{base_url}/reset-password?key={uidb64}&token={token}'
        context = {'name': name, 'link': reset_link}
        email_content =  render_to_string(
            template_name=template_name,
            context=context
            )
        
        email_message = EmailMessage(
        subject='[ASSUMATE Account] Password reset request',
        body=email_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
            )
        
        email_message.content_subtype = "html"

        email_message.send(fail_silently=False)
    
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['sender_id', 'chatroom_id', 'chatmess_content', 'chatmess_created_at', 'chatmess_is_read']

class ChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ['chatroom_id', 'chatroom_user_1', 'chatroom_user_2', 'chatroom_last_message']

class ChatUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fieds = ['user_prof_lname', 'user_prof_fname', 'user_prof_pic', 'user_id']    
    
class UserGoogleLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def check_user(self, _email):
        user_exist = UserModel.objects.get(email=_email)
        
        if user_exist:
            user = authenticate(username=user_exist.email, password=user_exist.password)
            if not user:
                return serializers.ValidationError('User not found')

        return user 

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user) 

        token['email'] = user.email
        token['user_id'] = user.id

        return token
    
class CarListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = '__all__'

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['wall_id', 'wall_amnt']

class ListingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Listing
        fields = '__all__' # Include other fields as necessary

class FavoriteSerializer(serializers.ModelSerializer):
    list_id = ListingSerializer()
    assumptor_id = UserProfileSerializer(source='user_id.userprofile', read_only=True)  # Ensure this is correct

    class Meta:
        model = Favorite
        fields = '__all__'

class FavoriteMarkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = '__all__'



###############################
###############################
class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        # fields = ['offer_id', 'offer_price', 'user_id', 'list_id', '']
        fields = '__all__'

        