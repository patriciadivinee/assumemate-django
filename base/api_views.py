from decimal import ROUND_DOWN, Decimal
import locale
import random
from django.shortcuts import redirect, render
from django.urls import reverse
import requests, base64, cloudinary
from smtplib import SMTPConnectError, SMTPException
# from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.db.models import F, Max, OuterRef, Subquery, Q, Case, When, Count
# from .permissions import IsAdminUser
from .models import UserProfile, UserVerification, ChatRoom, ChatMessage, Wallet, ListingApplication
from .serializers import *
from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.files.base import ContentFile
from rest_framework.authtoken.models import Token
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.contrib.auth import login as login, logout
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import update_last_login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from google.oauth2 import id_token as token_auth
from google.auth.transport import requests
import logging

logger = logging.getLogger(__name__)

load_dotenv()

clientId = os.getenv('PARTNER_CLIENT_ID')
secretKey = os.getenv('PARTNER_SECRET_KEY')
baseURL = os.getenv('PAYPAL_BASE_URL')

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class UserRegister(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            
            refresh_token = RefreshToken.for_user(user)
            access_token = str(refresh_token.access_token)
            
            return Response({'access': access_token, 'refresh': str(refresh_token), 'user': UserRegisterSerializer(user).data}, status=status.HTTP_201_CREATED)
        return Response({'error': serializer.error}, status=status.HTTP_400_BAD_REQUEST)

class UserCreateProfile(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        data = request.data
        user = UserModel.objects.get(id=data['user_id'])
        serializer = UserProfileSerializer(data=data)
        user_valid_id = request.data.get('user_prof_valid_id')
        user_picture = request.data.get('user_prof_pic')

        if serializer.is_valid(raise_exception=True):
            user_profile = serializer.save(user_id=user)

            UserApplication.objects.create(user_id=user)

            user = user_profile.user_id

            if not user.is_active:
                user.is_active = True
                user.save()

            if not user_valid_id or not user_picture:
                return Response({'error': 'No valid ID or picture provided'}, status=status.HTTP_400_BAD_REQUEST)
            
            images = [user_valid_id, user_picture]
            folder_name = f"{user_profile.user_prof_fname} {user_profile.user_prof_lname} ({user.id})"

            uploaded_images = []
            
            try:
                for img in images:
                    # format, imgstr = img.split(';base64,') 
                    ext = 'jpg'
                    
                    image_data = ContentFile(base64.b64decode(img), name=f"user{user.id}_{user_profile.user_prof_fname}_{user_profile.user_prof_lname}.{ext}")

                    upload_result = cloudinary.uploader.upload(image_data, folder=f"user_images/{folder_name}")

                    uploaded_images.append(upload_result['secure_url'] if image_data else None)

                if len(uploaded_images) == 2:
                    user_profile.user_prof_valid_id = uploaded_images[0]
                    user_profile.user_prof_pic = uploaded_images[1]
                else:
                    return JsonResponse({'error': 'Image upload failed.'}, status=status.HTTP_400_BAD_REQUEST)
                
                user_profile.save()

            except Exception as e:
                return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
            reserializer = UserProfileSerializer(user_profile)
            return Response({'user_profile': reserializer.data}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserEmailVerification(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        email = request.data.get('user_verification_email')
        existing_record = serializer.check_email(email=email)
        if existing_record:
            try:
                serializer.send_verification_email(request, existing_record.user_verification_email, existing_record.user_verification_code)
            except SMTPConnectError:
                return Response(
                    {'error': 'Unable to connect to the email server. Please try again later.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                        )
            except SMTPException as e:
                return Response({'error': 'Error sending verification code.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except requests.exceptions.ConnectionError:
                return Response({'error': 'Connection error. Please try again.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            return Response(EmailVerificationSerializer(existing_record).data, status=status.HTTP_200_OK)
        else:
            if serializer.is_valid(raise_exception=True):
                try:
                    verification = serializer.save()

                    try:
                        serializer.send_verification_email(request, verification.user_verification_email, verification.user_verification_code)
                    except SMTPConnectError:
                        return Response(
                            {'error': 'Unable to connect to the email server. Please try again later.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE
                        )
                    except SMTPException as e:
                        return Response({'error': 'Error sending verification code.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except requests.exceptions.ConnectionError:
                        return Response({'error': 'Connection error. Please try again.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

                    return Response(EmailVerificationSerializer(verification).data, status=status.HTTP_200_OK)
                except:
                    return Response({'error': str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmail(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, verification_code):
        try:
            verification = UserVerification.objects.get(user_verification_code=verification_code)

            if verification.user_verification_expires_at < timezone.now():
                return Response({'detail': 'Verification code has expired.'}, status=status.HTTP_400_BAD_REQUEST)
            verification.user_verification_is_verified = True
            verification.save()

            return HttpResponseRedirect(reverse('user-verified-page'))

        except UserVerification.DoesNotExist:
            return Response({'detail': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)
        
class CheckUserVerification(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = CheckUserVerifiedSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            is_verified, user_id = serializer.check_verification_status()
            return Response({'email': serializer.data,'is_verified': is_verified, 'user_account_id': user_id}, status=status.HTTP_200_OK)
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class UserLogin(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = [SessionAuthentication, TokenAuthentication]

    def post(self, request):
        data = request.data

        print(data)

        if 'token' in data:
            serializer = UserGoogleLoginSerializer(data=data)
        else:
            serializer = UserLoginSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            user = serializer.check_user(data)

            print(user)

            if user.is_staff or user.is_reviewer:
                role = 'Admin' if user.is_staff else 'Reviewer'
                return Response(
                    {'error': f'{role} users are not allowed to access this platform.'},
                    status=status.HTTP_403_FORBIDDEN)

            refresh_token = RefreshToken.for_user(user)
            access_token = str(refresh_token.access_token)

            user_role = {
                'is_admin': user.is_staff,
                'is_reviewer': user.is_reviewer,
                'is_assumee': user.is_assumee,
                'is_assumptor': user.is_assumptor
            }
            
            is_approved = False
            try:
                user_app = UserApplication.objects.get(user_id=user)
                print(user_app.user_app_status)
                is_approved = user_app.user_app_status
                print(is_approved)
            except (UserProfile.DoesNotExist,  UserApplication.DoesNotExist):
                return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

            response = {'access': access_token, 'refresh': str(refresh_token), 'user_role': user_role, 'user': {'user_id': user.id, 'email': user.email, 'is_approved': is_approved}}

            login(request, user)
            return Response(response, status=status.HTTP_200_OK)
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
# class UserGoogleLogin(APIView):
#     def post(self, request):
#         data = request.data
#         serializer = UserGoogleLoginSerializer(data=data)
        
#         if serializer.is_valid(raise_exception=True):
#             user = serializer.check_user(data)
#             token, created = Token.objects.get_or_create(user=user)

#             return Response({'token': token.key, 'user': serializer.data}, status=status.HTTP_200_OK)
        
#         return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
# class CheckGoogleEmail(APIView):
#     permission_classes = [permissions.AllowAny]
#     def post(self, request):
#         serializer = GoogleSignInCheckSerializer(data=request.data)

#         # print(request.data['token'])

#         if serializer.is_valid(raise_exception=True):
#             exists, data = serializer.check_email()

#             print(exists)

#             if not exists:
#                 return Response({'puta': data['google_id'], 'email': data['email']}, status=status.HTTP_200_OK)
#             else:
#                 return Response({'error': 'Account already exists.'}, status=status.HTTP_400_BAD_REQUEST)
#         else: 
#             print(serializer.errors)
#             return Response({'error': 'Credentials not provided'}, status=status.HTTP_400_BAD_REQUEST)

# class CheckGoogleEmail(APIView):
#     permission_classes = [permissions.AllowAny]
#     def post(self, request):
#         serializer = GoogleSignInCheckSerializer(data=request.data)

#         if serializer.is_valid(raise_exception=True):
#             print(exists)
#             exists, data = serializer.check_email()

#             print(exists)

#             if not exists:
#                 return Response({'credentials': data}, status=status.HTTP_200_OK)
#             else:
#                 return Response({'error': 'Account already exists.'}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({'error': 'Credentials not provided'}, status=status.HTTP_400_BAD_REQUEST)

class UserLogout(APIView):
    def post(self, request):
        try:
            # Attempt to retrieve the refresh token from the request data
            refresh_token = request.data.get('refresh')

            # If a refresh token is provided, blacklist it
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Perform the standard logout process
            logout(request)
            return Response(status=status.HTTP_200_OK)

        except Exception as e:
            # Handle errors (e.g., invalid or already blacklisted tokens)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class GetUserProfile(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        try:
            user_profile = UserProfile.objects.get(user_id=request.user.id)
            prof_serializer = UserProfileSerializer(user_profile)

            return Response({'user_profile': prof_serializer.data}, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UpdateUserProfile(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]        
    def put(self, request):
        try:
            user = UserProfile.objects.get(user_id=request.user.id)
            prof_serializer = UserProfileSerializer(user, data=request.data, partial=True)

            if prof_serializer.is_valid():
                prof_serializer.save()

                return Response({'user_profile': prof_serializer.data}, status=status.HTTP_200_OK)
            return Response(prof_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateUserProfilePicture(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]  

    def put(self, request):
        user_picture = request.data.get('user_prof_pic')

        print(user_picture)

        if not user_picture:
                return Response({'error': 'No picture provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_profile = request.user.profile

        folder_name = f"{user_profile.user_prof_fname} {user_profile.user_prof_lname} ({request.user.id})"
        
        try:
            # format, imgstr = img.split(';base64,') 
            ext = 'jpg'
            
            image_data = ContentFile(base64.b64decode(user_picture), name=f"user{request.user.id}_{user_profile.user_prof_fname}_{user_profile.user_prof_lname}.{ext}")

            print(image_data)

            upload_result = cloudinary.uploader.upload(image_data, folder=f"user_images/{folder_name}")

            print(upload_result)

            user_profile.user_prof_pic = upload_result['secure_url'] if image_data else None
            user_profile.save()

            return Response({'message': 'Profile picture updated successfully.', 'url': upload_result['secure_url']},
                            status=status.HTTP_200_OK)
        except Exception as e:
                error_message = str(e)

                if "upload" in error_message.lower():
                    error_message = "An error occurred while uploading the image. Please try again later."

                return JsonResponse({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordLink(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            serializer.create_token(email)
            serializer.send_reset_link(email)

            return Response({'message': 'Reset password request sent!'}, status=status.HTTP_200_OK)
    
# class VerifyPasswordResetToken(APIView):
#     permission_classes = [permissions.AllowAny]
#     def get(self, request, user, token):
#             user_id = request.GET.get('key')
#             token = request.GET.get('token')

#             verification = PasswordResetToken.objects.get(user=user)

#             if not verification.reset_token or verification.reset_token_expires_at < timezone.now() or PasswordResetToken.DoesNotExist:
#                 return render('base/forgot_password.html', context={'is_expired': True})
            

#             return redirect('find-password')
        


class ViewOtherProfile(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, user_id):
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            user_status = UserApplication.objects.get(user_id=user_id)
            prof_serializer = UserProfileSerializer(user_profile)

            profile_data = prof_serializer.data

            profile_data['application_status'] = user_status.user_app_status
            print(profile_data['application_status'])

            followers = Follow.objects.filter(following_id=user_id).count()
            profile_data['followers'] = followers
            print(followers)
            

            return Response({'user_profile': profile_data}, status=status.HTTP_200_OK)
        except UserApplication.DoesNotExist:
            return Response({'error': 'User application status not found.'}, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChangePasswordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def put(self, request):
        try:
            user = request.user
            
            currPassword = request.data.get('curr_password')
            newPassword = request.data.get('new_password')

            if not currPassword or not newPassword:
                return Response({'error': 'Current password and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user.check_password(currPassword):
                return Response({'error': 'Current password does not match.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if currPassword == newPassword:
                return Response({'error': 'New password cannot be the same as the current password.'}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(newPassword)
            user.save()
            refresh_token = RefreshToken.for_user(user)
            access_token = str(refresh_token.access_token)
            update_last_login(None, user)

            return Response({'access': access_token, 'refresh': str(refresh_token), 'message': 'Password updated successfully!'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetMessageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, receiver_id):
        # print(receiver_id)
        try:
            user_id = request.user.id

            user1, user2 = (user_id, receiver_id) if user_id > receiver_id else (receiver_id, user_id)
            room = ChatRoom.objects.get(chatroom_user_1=user1, chatroom_user_2=user2)
            room_messages = ChatMessage.objects.filter(chatroom_id=room)\
            .order_by('chatmess_created_at')\
            .values('sender_id', 'chatmess_content', 'chatmess_created_at', 'chatmess_is_read')
                    # serializer = MessageSerializer(room_messages, many=True)

            # print(room_messages)

            return Response({'messages': list(room_messages), 'room_id': f'{room.chatroom_id}'}, status=status.HTTP_200_OK)
        except ChatRoom.DoesNotExist:
            return Response({'detail': 'Chat room not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class MakeOfferAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user
        list_id = request.data.get('listing_id')

        try:
            list = Listing.objects.get(list_id=list_id)
        except Listing.DoesNotExist:
            return Response({'error': 'Listing not found.'}, status=status.HTTP_404_NOT_FOUND)

        receiver_id = list.user_id.id
        price = request.data.get('offer_price')
        locale.setlocale(locale.LC_ALL, 'en_PH.UTF-8')
            # double_amnt = double
        formatted_amount = locale.currency(float(price), grouping=True)

        print(formatted_amount)

        existing_offer = Offer.objects.filter(list_id__user_id=receiver_id, user_id=user, offer_status__in=['PENDING', 'ACCEPTED']).first()

        if existing_offer:
            print(existing_offer)
            return Response({
                'error': 'You still have an active offer for this listing.'
            }, status=status.HTTP_400_BAD_REQUEST)


        try:
            Offer.objects.create(offer_price=price, list_id=list, user_id=user)
            
            try:
                receiver = UserModel.objects.get(pk=receiver_id)
            except UserModel.DoesNotExist:
                return Response({'error': 'Recipient not found.'}, status=status.HTTP_404_NOT_FOUND)
            
            chat_content = {'text': f'Made an offer: {formatted_amount}',
                            'file': None,
                            'file_type': None}
            
            chat_room, created = ChatRoom.objects.get_or_create(
                chatroom_user_1=max(user, receiver, key=lambda u: u.id),
                chatroom_user_2=min(user, receiver, key=lambda u: u.id),
                defaults={'chatroom_last_message': chat_content}
            )

            chat_room.chatroom_last_message = chat_content['text']
            chat_room.save()

            chat_message_data = {
                'chatmess_content': chat_content,
                'sender_id': user.id,
                'chatroom_id': chat_room.chatroom_id
            }

            serializer = MessageSerializer(data=chat_message_data)
            if serializer.is_valid():
                serializer.save()
                return Response({'user_id': receiver_id, 'room_id': chat_room.chatroom_id}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)                

        except Exception as e:
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateOfferAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request):
        offer_id = request.data.get('offer_id')
        offer_amnt = request.data.get('offer_amnt')

        user = request.user

        try:
            offer = Offer.objects.get(offer_id=offer_id)

            lister = UserModel.objects.get(pk=offer.list_id.user_id)

            group = ''
            if user.id > lister.id:
                group = f'{user.id}-{lister.id}'
            elif lister.id > user.id:
                group = f'{lister.id}-{user.id}'

            if offer.offer_status != 'PENDING':
                return Response({'error': 'Cannot change offer amount'}, status=status.HTTP_400_BAD_REQUEST)
            
            offer.offer_price = offer_amnt
            offer.save()

            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f'chat_{group}',
                {
                    'type': 'offer_update',
                    'message': f'Offer {offer_id} updated to {offer_amnt}',
                }
            )

            return Response({})

        except Offer.DoesNotExist:
            return Response({'error': 'Offer not found'}, status=status.HTTP_400_BAD_REQUEST)
        

class GetActiveOfferAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, receiver_id):
        receiver_id = receiver_id
        print(request.user.id)
        print(receiver_id)
        try:
            user = request.user

            lastest_active_offer = Offer.objects.filter(user_id=user.id,
                list_id__user_id=receiver_id,
                offer_status__in=['PENDING', 'ACCEPTED']
                ).select_related('list_id__user_id__profile').order_by('-offer_created_at').first()
            
            if lastest_active_offer:
                offer = OfferSerializer(lastest_active_offer).data
                listing = CarListingSerializer(lastest_active_offer.list_id).data
                lister = lastest_active_offer.list_id.user_id.profile
                lister_prof = UserProfileSerializer(lister).data

                print(offer)
                print(lister_prof)
                print(listing)

                return Response({'offer': offer, 'listing': listing, 'lister_profile': lister_prof}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'No active offers found'}, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class AssumptorListOffers(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            assumptor = request.user

            offers = Offer.objects.filter(Q(list_id__user_id=assumptor) and Q(offer_status='PENDING'))


            serialized_offers = OfferSerializer(offers, many=True).data

            try:

                for offer in serialized_offers:
                    listing = Listing.objects.get(list_id=offer['list_id'])
                    listing_deets = CarListingSerializer(listing).data
                    offer['list_image'] = listing_deets['list_content']['images'][0]

                    user = UserProfile.objects.get(user_id=offer['user_id'])
                    user_prof = UserProfileSerializer(user).data
                    offer['user_fullname'] = user_prof['user_prof_fname'] + ' ' + user_prof['user_prof_lname']

                    chat_room = ChatRoom.objects.get(
                    chatroom_user_1=max(user.user_id, assumptor, key=lambda u: u.id),
                    chatroom_user_2=min(user.user_id, assumptor, key=lambda u: u.id)
                        )
                    
                    offer['chatroom_id'] = chat_room.chatroom_id
            except Offer.DoesNotExist or Listing.DoesNotExist or UserProfile.DoesNotExist or ChatRoom.DoesNotExist or UserModel.DoesNotExist:
                return Response({'error': 'Resquest invalid'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({'offers': serialized_offers}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': f'Unexpected error occured: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetListingOfferAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, receiver_id):
        receiver_id = receiver_id
        print(request.user.id)
        print(receiver_id)
        try:
            user = request.user

            lastest_active_offer = Offer.objects.filter(user_id=receiver_id,
                list_id__user_id=user.id,
                offer_status__in=['PENDING', 'ACCEPTED']
                ).select_related('list_id__user_id__profile').order_by('-offer_created_at').first()
            
            if lastest_active_offer:
                offer = OfferSerializer(lastest_active_offer).data
                listing = CarListingSerializer(lastest_active_offer.list_id).data
                lister = lastest_active_offer.list_id.user_id.profile
                lister_prof = UserProfileSerializer(lister).data

                return Response({'offer': offer, 'listing': listing, 'lister_profile': lister_prof}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'No active offers found'}, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserChatRoomAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        try:
            user_id = request.user.id

            rooms = ChatRoom.objects.filter(Q(chatroom_user_1=user_id) | Q(chatroom_user_2=user_id)).values('chatroom_id', 'chatroom_last_message')
            chatmates = ChatRoom.objects.filter(
                Q(chatroom_user_1=user_id) | Q(chatroom_user_2=user_id)
            ).annotate(
                chatmate=Case(
                    When(chatroom_user_1=user_id, then=F('chatroom_user_2')),
                    When(chatroom_user_2=user_id, then=F('chatroom_user_1'))
                ),
                last_message_date=Max('messages__chatmess_created_at'),
                last_sender_id=Subquery(
                    ChatMessage.objects.filter(
                        chatroom_id=OuterRef('chatroom_id')
                    ).order_by('-chatmess_created_at').values('sender_id')[:1]),
                isRead=Subquery(
                    ChatMessage.objects.filter(
                        chatroom_id=OuterRef('chatroom_id')
                    ).order_by('-chatmess_created_at').values('chatmess_is_read')[:1]),
            ).values('chatmate', 'chatroom_id', 'chatroom_last_message', 'last_message_date', 'last_sender_id', 'isRead')
                        
            chatmates_info = UserModel.objects.filter(id__in=chatmates.values('chatmate')).values(
                'id',
                'profile__user_prof_fname',
                'profile__user_prof_lname',
                'profile__user_prof_pic'
            )
            
            inbox = []
            for room in chatmates:
                chatmate_profile = next((info for info in chatmates_info if info['id'] == room['chatmate']), None)
                
                inbox.append({
                    'chatroom_id': room['chatroom_id'],
                    'chatmate_id': room['chatmate'],
                    'chatmate_name': f"{chatmate_profile['profile__user_prof_fname']} {chatmate_profile['profile__user_prof_lname']}" if chatmate_profile else None,
                    'chatmate_pic':chatmate_profile['profile__user_prof_pic'],
                    'last_message': room['chatroom_last_message'],
                    'last_message_date': room['last_message_date'],
                    'sender_id': room['last_sender_id'],
                    'mess_isread': room['isRead']
                })
            
            inbox = sorted(inbox, key=lambda x: x['last_message_date'], reverse=True)

            print(chatmates)
            print(user_id)
            print(inbox)

            return Response({'rooms': inbox, }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CarListingCreate(generics.CreateAPIView):
    queryset = Listing.objects.all()
    serializer_class = CarListingSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Validate the data
        list_instance = self.perform_create(serializer)

        ListingApplication.objects.create(list_id=list_instance)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def perform_create(self, serializer):
        instance = serializer.save(user_id=self.request.user)
        
        return instance

@method_decorator(csrf_exempt, name='dispatch')
class CarListingByCategoryView(APIView):
    serializer_class = CarListingSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get_queryset(self):
        category = self.kwargs.get('category')
        return Listing.objects.filter(list_content__category=category)

    def get(self, request, category, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')   
class ListingDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request, list_id, *args, **kwargs):
        listing = get_object_or_404(Listing, list_id=list_id)
        serializer = CarListingSerializer(listing)
        # print(serializer.data)
        return Response(serializer.data)

class AddCoinsToWalletView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = WalletSerializer

    def get_object(self):
        user = self.request.user
        wallet = Wallet.objects.filter(user_id=user.id).first()
        
        if not wallet:
            raise Http404("Wallet not found for the user.")
        
        return wallet

    def perform_update(self, serializer):
        instance = self.get_object()  # Get the wallet instance
        coins_to_add = self.request.data.get('coins_to_add', 0)

        coins_to_add = Decimal(coins_to_add)

        instance.wall_amnt += coins_to_add
        instance.save()

        return Response({'new_balance': instance.wall_amnt}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class GetTotalCoinsView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

    def get_object(self):
        user = self.request.user
        try:
            # Try to retrieve the wallet for the logged-in user
            wallet = Wallet.objects.get(user_id=user.id)
        except Wallet.DoesNotExist:
            # If wallet doesn't exist, create a new one with default values
            wallet = Wallet.objects.create(user_id=user.id, wall_amnt=0)
            wallet.save()
        
        return wallet

    def get(self, request, *args, **kwargs):
        # Get the wallet and serialize the data
        wallet = self.get_object()
        serializer = self.get_serializer(wallet)
        return Response(serializer.data)

class DeductCoinsView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = WalletSerializer

    def get_object(self):
        return Wallet.objects.get(user_id=self.request.user)

    def update(self, request, *args, **kwargs):
        wallet = self.get_object()
        amount_to_deduct = request.data.get("amount", 0)
        amount_to_deduct = Decimal(amount_to_deduct)

        # Check if the list_id is provided in the request
        list_id = request.data.get("list_id")
        if not list_id:
            return Response({'error': 'list_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the listing is already promoted
        if PromoteListing.objects.filter(list_id=list_id).exists():
            return Response({'Listing is already promoted.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for sufficient coins
        if wallet.wall_amnt < amount_to_deduct:
            return Response({'error': 'Insufficient coins'}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct coins and save wallet
        wallet.wall_amnt -= amount_to_deduct
        wallet.save()
        return Response({'new_balance': wallet.wall_amnt})

class DeleteListingView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = CarListingSerializer

    def update(self, request, *args, **kwargs):
        listing_id = kwargs.get("listing_id")
        
        # Check if the listing exists in PromoteListing and delete it if found
        try:
            promote_listing = PromoteListing.objects.get(list_id=listing_id)
            promote_listing.delete()
        except PromoteListing.DoesNotExist:
            pass  # No action needed if listing is not promoted

        # Check if the listing exists in the Listing table
        try:
            listing = Listing.objects.get(list_id=listing_id)
            listing.list_status = "archive"  # Set status to 'archive'
            listing.save()
            return Response({"message": "Listing deleted successfully"}, status=status.HTTP_200_OK)
        except Listing.DoesNotExist:
            raise Exception({"error": "Listing not found"})
        
class UpdateListingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, listing_id):
        try:
            # Fetch the listing by ID
            listing = Listing.objects.get(list_id=listing_id)

            # Get the amount from the request body
            amount = request.data.get("amount", 0)
            amount = Decimal(amount)

            # Update the list_status to 'active'
            listing.list_status = 'active'
            listing.save() 

            # Create a transaction for the listing status update
            transaction = Transaction.objects.create(
                user_id=request.user,
                amount=amount,  # Use the amount passed from the request
                transaction_status='COMPLETED',
                transaction_date=timezone.now(),
                category='ADD LISTING'
            )

            # Return a success response
            return Response({
                "message": "Listing status updated successfully.",
                "transaction_id": transaction.id
            }, status=200)
        except Listing.DoesNotExist:
            # If the listing doesn't exist, return a 404 response
            raise Exception(detail="Listing not found.")

class ListingByCategoryView(APIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, category, *args, **kwargs):
        queryset = Listing.objects.filter(list_content__category=category)
        if queryset.exists():
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data)
        else:
            # Return an empty list if no listings are found for the category
            return Response([], status=200)

class ListingDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request, list_id, *args, **kwargs):
        listing = get_object_or_404(Listing, list_id=list_id)
        serializer = ListingSerializer(listing)
        return Response(serializer.data)
    
class AssumptorListings(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request):
        user = request.user.id


        listings = Listing.objects.filter(user_id=user)

        if listings.exists():
            serializer = ListingSerializer(listings, many=True)
            
            return Response({'listings': serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No listing available'}, status=status.HTTP_204_NO_CONTENT)
        
class AssumptorViewListings(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request, user_id):
        user = UserModel.objects.get(id=user_id)

        listings = Listing.objects.filter(user_id=user)

        if listings.exists():
            serializer = ListingSerializer(listings, many=True)
            
            return Response({'listings': serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No listing available'}, status=status.HTTP_204_NO_CONTENT)
    
class RandomListingListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request):
        user_id = request.user.id  # Get the authenticated user's ID

        # Count listings and determine how many to return
        total_listings = Listing.objects.exclude(user_id=user_id).aggregate(count=Count('user_id'))['count']
        listings_to_return = 10 if total_listings >= 10 else total_listings
        
        # Fetch all listings excluding the user's own listings and select a random sample
        all_listings = list(Listing.objects.exclude(user_id=user_id))
        
        # Ensure there are listings to sample from
        if not all_listings:
            return Response([], status=status.HTTP_200_OK)  # Return an empty list if no listings available

        random_listings = random.sample(all_listings, min(listings_to_return, len(all_listings)))

        # Serialize and return the random listings
        serializer = ListingSerializer(random_listings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FavoritesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request):
        user = request.user
        favorites = Favorite.objects.filter(user_id=user).order_by('-fav_date')
        
        # Serialize the favorites, which includes the nested listings
        serializer = FavoriteSerializer(favorites, many=True)

        # Log the serialized data to verify its structure
        print('Favorites Data:', serializer.data)  # Log the serialized data
        #print(f"Listing Content for Favorite ID {favorites.fav_id}: {favorites.list_content}")
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class FavoritesMarkView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request):
        user = request.user
        favorites = Favorite.objects.filter(user_id=user)
        
        # Serialize the favorites, which includes the nested listings
        serializer = FavoriteMarkSerializer(favorites, many=True)

        # Log the serialized data to verify its structure
        print('Favorites Data:', serializer.data)  # Log the serialized data
        #print(f"Listing Content for Favorite ID {favorites.fav_id}: {favorites.list_content}")
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AddFavoriteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def post(self, request):
        user = request.user
        listing_id = request.data.get('listing_id')

        # Log the received listing ID
        print(f"Received listing_id: {listing_id} from user: {user.id}")

        # Fetch the listing object using the correct field name
        listing = get_object_or_404(Listing, pk=listing_id)

        # Check if the favorite already exists
        favorite, created = Favorite.objects.get_or_create(list_id=listing, user_id=user)

        if created:
            print(f"Added favorite for user {user.id} on listing {listing_id} at {timezone.now()}")
            return Response({'message': 'Added to favorites'}, status=status.HTTP_201_CREATED)
        else:
            print(f"Favorite already exists for user {user.id} on listing {listing_id}")
            return Response({'message': 'Already in favorites'}, status=status.HTTP_400_BAD_REQUEST)

class RemoveFavoriteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request):
        user = request.user
        list_id = request.data.get('list_id')  # Get the fav_id from the request

        try:
            favorite = Favorite.objects.get(list_id=list_id, user_id=user)  # Use fav_id to find the favorite
            favorite.delete()
            return Response({'message': 'Removed from favorites'}, status=status.HTTP_200_OK)
        except Favorite.DoesNotExist:
            return Response({'error': 'Favorite not found'}, status=status.HTTP_404_NOT_FOUND)
        
class UserProfileView(APIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request, user_id):
        try:
            # Fetch the user profile based on the provided user_id
            user_profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the user profile data
        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')         
class ListingSearchView(APIView):
    """
    View to search listings or return all listings when no search query is provided.
    """
    serializer_class = CarListingSerializer
    permission_classes = [permissions.AllowAny] 

    def get(self, request, *args, **kwargs):
        query = self.request.query_params.get('query', None)
        category = self.request.query_params.get('category', None)  
        logger.debug(f'Received search query: {query}, category: {category}')

        listings = Listing.objects.all()  
        if category:
            listings = listings.filter(category__name=category)  
        if query:
            listings = listings.filter(title__icontains=query) 
        
        logger.debug(f'Listings found: {listings.count()}') 

        if not listings.exists():
            logger.warning('No listings found') 
            return Response({'message': 'No listings found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(listings, many=True)
        logger.debug(f'Serialized data: {serializer.data}') 
        return Response(serializer.data, status=status.HTTP_200_OK)

def is_admin(user):
    return user.is_staff

###### render views ######

def email_verified(request):
    return render(request, 'base/email-verified.html')

class CheckGoogleEmail(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')

        # print(token)

        if not token:
            return JsonResponse({'error': 'No token provided'}, status=400)

        try:
            clientId = os.getenv('OAUTH_CLIENT_ID')

            print(clientId)
            
            id_info = token_auth.verify_oauth2_token(token, requests.Request(), clientId)

            print(id_info)

            google_id = id_info['sub'] 
            email = id_info['email']

            user = UserModel.objects.filter(google_id=google_id).first() or UserModel.objects.filter(email=email).first()

            if user:
                return Response({'error': 'Account already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse({'status': 'success', 'google_id': google_id, 'email': email}, status=status.HTTP_200_OK)
        except ValueError as e:
            print(e)
            return JsonResponse({'error': f'Invalid token: {e}'}, status=status.HTTP_400_BAD_REQUEST)


class FollowUser(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = FollowSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        # Extract assumptor_user from the incoming data
        data['following_id'] = data.get('user_id')  # Ensure you set the correct field name
        data['follower_id'] = request.user.id  # Get the current user's ID

        # Debugging: Log the data being sent to the serializer
        print("Incoming data for serializer:", data)

        # Create the serializer instance with the corrected data
        serializer = self.serializer_class(data=data)

        # Validate and save the serializer data
        if serializer.is_valid():
            serializer.save()
            following = serializer.data
            print(following)
            try:
                id = following['following_id']
                user = UserModel.objects.get(id=id)
            except UserModel.DoesNotExist:
                return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)
                
            try:
                prof = UserProfile.objects.get(user_id=user)
            except UserProfile.DoesNotExist:
                return Response({'error': 'User profile does not exist'}, status=status.HTTP_404_NOT_FOUND)

            # Prepare the follower data for response
            following_data = {
                'user_id': prof.user_id.id, 
                'fullname': prof.user_prof_fname + ' ' + prof.user_prof_lname,
                'profile': prof.user_prof_pic
            }
            print(following_data)
            return Response(following_data, status=status.HTTP_200_OK)
        # Log serializer errors for debugging
        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UnfollowUser(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = Follow.objects.all()

    def delete(self, request, *args, **kwargs):
        print("Received DELETE request")  # Debugging line
        print("User:", request.user)  # Print the authenticated user
        print("Request data:", request.data)  # Print the request data
        
        user_id = request.data.get('user_id')
        print("User ID to unfollow:", user_id)  # Print the user ID to unfollow

        if user_id is None:
            print("No user_id provided in the request.")  # Debugging line
            return Response({"detail": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            following = self.queryset.get(follower_id=request.user, following_id=user_id)
            following.delete()
            print(f"Successfully unfollowed user ID {user_id}")  # Debugging line
            return Response({"detail": "Unfollowed successfully."}, status=status.HTTP_200_OK)
        except Follow.DoesNotExist:
            print(f"Following relationship does not exist for user ID {user_id}")  # Debugging line
            return Response({"detail": "Following relationship does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("An error occurred:", str(e))  # Debugging line for any other exceptions
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class ListFollowing(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        followings = Follow.objects.filter(follower_id=request.user)
        serializer = FollowSerializer(followings, many=True)
        print(serializer.data)
        following = serializer.data
        following_list = []
        for follow in following:
            try:
                id = follow['following_id']
                user = UserModel.objects.get(id=id)
            except UserModel.DoesNotExist:
                return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)
                
            try:
                prof = UserProfile.objects.get(user_id=user)
            except UserProfile.DoesNotExist:
                return Response({'error': 'User profile does not exist'}, status=status.HTTP_404_NOT_FOUND)

            # Prepare the follower data for response
            following_data = {
                'user_id': prof.user_id.id, 
                'fullname': prof.user_prof_fname + ' ' + prof.user_prof_lname,
                'profile': prof.user_prof_pic
            }

            following_list.append(following_data)
        print(following_list)
        return Response({'following': following_list}, status=status.HTTP_200_OK)


class ListFollower(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        followers = Follow.objects.filter(following_id=request.user)
        serializer = FollowSerializer(followers, many=True)
        # print(serializer.data)
        follower = serializer.data
        follower_list = []
        for follow in follower:
            try:
                id = follow['follower_id']
                user = UserModel.objects.get(id=id)
            except UserModel.DoesNotExist:
                return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)
                
            try:
                prof = UserProfile.objects.get(user_id=user)
            except UserProfile.DoesNotExist:
                return Response({'error': 'User profile does not exist'}, status=status.HTTP_404_NOT_FOUND)

            follower_data = {
                'user_id': prof.user_id.id,  
                'fullname': prof.user_prof_fname + ' ' + prof.user_prof_lname,
                'profile': prof.user_prof_pic  
            }

            follower_list.append(follower_data)
            
        print(follower_list)
        return Response({'follower': follower_list}, status=status.HTTP_200_OK)
    

class TransactionHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        # Fetch all transactions for the authenticated user
        user = request.user
        transactions = Transaction.objects.filter(user_id=user)  # Assuming user_id is the user who made the transaction

        # Serialize the data
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class CreatePaypalOrder(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        url = "https://api.sandbox.paypal.com/v2/checkout/orders"
        client_id = clientId
        secret_key = secretKey
        credentials = f"{client_id}:{secret_key}"
        auth_header = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
            "Content-Type": "application/json"
        }

        amount = request.data.get('amount', '10.00')

        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "PHP",
                    "value": str(amount),
                }
            }],
            "application_context": {
                "return_url": "http://yourapp.com/payment-success",
                "cancel_url": "http://yourapp.com/payment-cancelled",
                "user_action": "PAY_NOW",
                "shipping_preference": "NO_SHIPPING",
            }
        }

        try:
            response = requests.post(url, json=order_data, headers=auth_header)
            response.raise_for_status()
            
            order_data = response.json()
            return Response({
                'id': order_data['id'],
                'approval_url': next(link['href'] for link in order_data['links'] if link['rel'] == 'approve')
            })
        except requests.exceptions as e:
            logger.error(f"PayPal API error: {str(e)}")
            return Response({'error': 'Unable to create PayPal order'}, status=500)
        
class CapturePaypalOrder(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        order_id = request.data.get('orderID')
        amount = request.data.get('amount')

        if not order_id:
            return Response({'error': 'Missing orderID'}, status=400)

        client_id = clientId
        secret_key = secretKey
        credentials = f"{client_id}:{secret_key}"
        auth_header = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
            "Content-Type": "application/json"
        }

        capture_url = f"https://api.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"

        try:
            capture_response = requests.post(capture_url, headers=auth_header)
            capture_response.raise_for_status()
            
            capture_data = capture_response.json()
            
            # Extract capture details from the response
            capture_id = capture_data['purchase_units'][0]['payments']['captures'][0]['id']
            transaction_status = capture_data['status']  # e.g., 'COMPLETED'
            capture_amount = capture_data['purchase_units'][0]['payments']['captures'][0]['amount']['value']
             # Retrieve the UserAccount instance associated with the currently authenticated user
            user_account = request.user

            # Create a new transaction and link it to the logged-in user
            transaction = Transaction.objects.create(
                order_id=order_id,
                capture_id=capture_id,
                amount=capture_amount,
                transaction_status=transaction_status,
                transaction_date=timezone.now(),  # Set the current timestamp
                user_id=user_account  # Link the UserAccount instance directly
            )

            return Response({
                'status': 'COMPLETED',
                'order_id': order_id,
                'capture_id': capture_id,
                'amount': capture_amount,
                'transaction_id': transaction.id  # Return the transaction ID for reference
            })
        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal capture error: {str(e)}")
            return Response({'error': 'Payment capture failed'}, status=500)
        
class PaypalPaymentCancelled(APIView):
        def get(self, request, *args, **kwargs):
                # You can handle cancellation logic here, such as notifying the user
                return JsonResponse({'status': 'Payment cancelled'})
        
@method_decorator(csrf_exempt, name='dispatch')
class RefundPayment(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        try:
            # Query the first transaction in the database
            transaction = Transaction.objects.last()

            if not transaction:
                return JsonResponse({"error": "No transaction found"}, status=404)

            # Prepare the refund request data
            capture_id = transaction.capture_id

            if not capture_id:
                return JsonResponse({"error": "Missing capture_id"}, status=400)
                
            # Verify transaction status
            if transaction.transaction_status != 'COMPLETED':
                return JsonResponse({
                    "error": f"Cannot refund transaction with status: {transaction.transaction_status}"
                }, status=400)

            # Get OAuth token first
            auth_url = "https://api.sandbox.paypal.com/v1/oauth2/token"
            client_id = clientId
            secret_key = secretKey
            credentials = f"{client_id}:{secret_key}"
            refund_amount = (transaction.amount * Decimal('0.95')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            # Get access token
            auth_response = requests.post(
                auth_url,
                headers={
                    "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"grant_type": "client_credentials"}
            )
            
            auth_response.raise_for_status()
            access_token = auth_response.json()['access_token']

            # Correct refund URL
            url = f"https://api.sandbox.paypal.com/v2/payments/captures/{capture_id}/refund"
            
            refund_data = {
                "amount": {
                    "currency_code": "PHP",
                    "value": str(refund_amount)
                },
                "note_to_payer": "Refund for transaction"
            }

            # Make the refund request with OAuth token
            response = requests.post(
                url,
                json=refund_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
            )
            
            # Log the response for debugging
            logger.info(f"PayPal Refund Request Details:")
            logger.info(f"Capture ID: {capture_id}")
            logger.info(f"Amount: {transaction.amount}")
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Content: {response.text}")
            
            response.raise_for_status()

            # Parse the PayPal response
            refund_response = response.json()

            # Update transaction status
            transaction.transaction_status = "REFUNDED"
            transaction.save()

            # Return success response
            return JsonResponse({
                "message": "Refund successful",
                "transaction_id": transaction.id,
                "order_id": transaction.order_id,
                "refund_id": refund_response.get('id', 'N/A'),
                "status": refund_response.get('status'),
                "amount": str(transaction.amount),
                "refund_date": timezone.now().isoformat()
            }, status=200)

        except requests.exceptions.RequestException as e:
            logger.error(f"Refund failed: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"PayPal error details: {e.response.text}")
            return JsonResponse({
                "error": "Refund request failed",
                "details": str(e),
                "transaction_id": transaction.id if transaction else None
            }, status=500)
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            return JsonResponse({
                "error": "Internal server error",
                "details": str(e)
            }, status=500)