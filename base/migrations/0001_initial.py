# Generated by Django 5.1.1 on 2025-01-08 01:24

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('username', models.CharField(blank=True, max_length=150, null=True, unique=True)),
                ('google_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('is_reviewer', models.BooleanField(default=False)),
                ('is_assumee', models.BooleanField(default=False)),
                ('is_assumptor', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=False)),
                ('fcm_token', models.CharField(blank=True, max_length=255, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'user_account',
            },
        ),
        migrations.CreateModel(
            name='Paypal',
            fields=[
                ('user_id', models.OneToOneField(db_column='user_id', editable=False, on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='paypal', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('paypal_merchant_id', models.CharField(max_length=255, unique=True)),
                ('paypal_linked_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'user_paypal',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('user_prof_fname', models.CharField(max_length=50)),
                ('user_prof_lname', models.CharField(max_length=50)),
                ('user_prof_gender', models.CharField(max_length=6)),
                ('user_prof_dob', models.DateField()),
                ('user_prof_mobile', models.CharField(max_length=13, unique=True)),
                ('user_prof_address', models.CharField(max_length=255)),
                ('user_prof_pic', models.URLField(default='https://res.cloudinary.com/dbroe2hjh/image/upload/v1733245571/no-profile_xnyyoi.jpg')),
                ('user_prof_valid_pic', models.URLField(default='https://res.cloudinary.com/dbroe2hjh/image/upload/v1733245571/no-profile_xnyyoi.jpg')),
                ('user_prof_valid_id', models.URLField()),
                ('user_id', models.OneToOneField(db_column='user_id', editable=False, on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='profile', serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_profile',
            },
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('user_id', models.OneToOneField(db_column='user_id', editable=False, on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('wall_amnt', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'wallet',
            },
        ),
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('chatroom_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('chatroom_last_message', models.TextField(blank=True, null=True)),
                ('chatroom_user_1', models.ForeignKey(db_column='chatroom_user_1', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_id_1', to=settings.AUTH_USER_MODEL)),
                ('chatroom_user_2', models.ForeignKey(db_column='chatroom_user_2', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_id_2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'chat_room',
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('chatmess_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('chatmess_content', models.JSONField()),
                ('chatmess_created_at', models.DateTimeField(auto_now_add=True)),
                ('chatmess_is_read', models.BooleanField(default=False)),
                ('sender_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.PROTECT, related_name='messages', to=settings.AUTH_USER_MODEL)),
                ('chatroom_id', models.ForeignKey(db_column='chatroom_id', on_delete=django.db.models.deletion.PROTECT, related_name='messages', to='base.chatroom')),
            ],
            options={
                'db_table': 'chat_message',
            },
        ),
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('follower_id', models.ForeignKey(db_column='follower_id', on_delete=django.db.models.deletion.CASCADE, related_name='following', to=settings.AUTH_USER_MODEL)),
                ('following_id', models.ForeignKey(db_column='following_id', on_delete=django.db.models.deletion.CASCADE, related_name='follower', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'follow',
            },
        ),
        migrations.CreateModel(
            name='Listing',
            fields=[
                ('list_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('list_content', models.JSONField(blank=True, null=True)),
                ('list_status', models.CharField(choices=[('PENDING', 'Pending'), ('ACTIVE', 'Active'), ('RESERVED', 'Reserved'), ('SOLD', 'Sold'), ('ARCHIVED', 'Archived')], default='PENDING', max_length=20)),
                ('list_duration', models.DateTimeField(blank=True, null=True)),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.PROTECT, related_name='listing', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'listing',
            },
        ),
        migrations.CreateModel(
            name='LikeLog',
            fields=[
                ('log_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('log_date', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
            ],
            options={
                'db_table': 'like_log',
            },
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('fav_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('fav_date', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
            ],
            options={
                'db_table': 'favorite',
            },
        ),
        migrations.CreateModel(
            name='ListingApplication',
            fields=[
                ('list_app_id', models.AutoField(primary_key=True, serialize=False)),
                ('list_app_status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=20)),
                ('list_app_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('list_reason', models.CharField(max_length=255, null=True)),
                ('list_app_reviewer_id', models.ForeignKey(blank=True, db_column='user_app_reviewer_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='listing_reviews', to=settings.AUTH_USER_MODEL)),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
            ],
            options={
                'db_table': 'listing_application',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('notif_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('notif_message', models.CharField(max_length=255)),
                ('notif_created_at', models.DateTimeField(auto_now_add=True)),
                ('notif_is_read', models.BooleanField(default=False)),
                ('notification_type', models.CharField(default='general', max_length=50)),
                ('follow_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='base.follow')),
                ('list_id', models.ForeignKey(blank=True, db_column='list_id', null=True, on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
                ('recipient', models.ForeignKey(db_column='recipient_id', on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('triggered_by', models.ForeignKey(blank=True, db_column='triggered_by_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='triggered_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'notification',
                'ordering': ['-notif_created_at'],
            },
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('offer_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('offer_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('offer_status', models.CharField(choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('PAID', 'Paid'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=15)),
                ('offer_created_at', models.DateTimeField(auto_now_add=True)),
                ('offer_updated_at', models.DateTimeField(auto_now=True)),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, related_name='offer', to='base.listing')),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='offer', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'offer',
            },
        ),
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reset_token', models.TextField(blank=True, null=True)),
                ('reset_token_created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('reset_token_expires_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='reset_password', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'password_reset_token',
            },
        ),
        migrations.CreateModel(
            name='PromoteListing',
            fields=[
                ('prom_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('prom_start', models.DateTimeField()),
                ('prom_end', models.DateTimeField()),
                ('list_id', models.ForeignKey(db_column='list_id', on_delete=django.db.models.deletion.CASCADE, to='base.listing')),
            ],
            options={
                'db_table': 'promote_listing',
            },
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('rate_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('rating_value', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])),
                ('review_comment', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('from_user_id', models.ForeignKey(db_column='from_user_id', on_delete=django.db.models.deletion.CASCADE, related_name='ratings_given', to=settings.AUTH_USER_MODEL)),
                ('list_id', models.ForeignKey(db_column='list_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='base.listing')),
                ('to_user_id', models.ForeignKey(db_column='to_user_id', on_delete=django.db.models.deletion.CASCADE, related_name='ratings_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'rating',
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('report_id', models.AutoField(primary_key=True, serialize=False)),
                ('report_details', models.JSONField(null=True)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('report_status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=20)),
                ('report_reason', models.JSONField(null=True)),
                ('reviewer', models.ForeignKey(db_column='user_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reviewed_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'report',
            },
        ),
        migrations.CreateModel(
            name='ReservationInvoice',
            fields=[
                ('order_id', models.BigAutoField(db_column='invoice_id', editable=False, primary_key=True, serialize=False)),
                ('order_price', models.DecimalField(db_column='invoice_price', decimal_places=2, max_digits=12)),
                ('order_status', models.CharField(db_column='invoice_status', default='PENDING', max_length=255)),
                ('order_created_at', models.DateTimeField(auto_now_add=True, db_column='invoice_created_at')),
                ('order_updated_at', models.DateTimeField(auto_now=True, db_column='invoice_updated_at')),
                ('list_id', models.ForeignKey(blank=True, db_column='list_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.listing')),
                ('offer_id', models.ForeignKey(blank=True, db_column='offer_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.offer')),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.PROTECT, related_name='invoice', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'invoice',
            },
        ),
        migrations.CreateModel(
            name='RefundRequest',
            fields=[
                ('refund_id', models.BigAutoField(db_column='refund_id', editable=False, primary_key=True, serialize=False)),
                ('refund_status', models.CharField(choices=[('PENDING', 'Pending'), ('REFUNDED', 'Approved')], default='PENDING', max_length=15)),
                ('paypal_refund_id', models.CharField(blank=True, max_length=255, null=True)),
                ('refund_created_at', models.DateTimeField(auto_now_add=True)),
                ('refund_updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.PROTECT, related_name='refund_request', to=settings.AUTH_USER_MODEL)),
                ('order_id', models.OneToOneField(db_column='order_id', on_delete=django.db.models.deletion.PROTECT, related_name='refund_request', to='base.reservationinvoice')),
            ],
            options={
                'db_table': 'refund_request',
            },
        ),
        migrations.CreateModel(
            name='PayoutRequest',
            fields=[
                ('payout_id', models.BigAutoField(db_column='payout_id', editable=False, primary_key=True, serialize=False)),
                ('payout_paypal_email', models.EmailField(max_length=254)),
                ('payout_status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Approved'), ('REJECTED', 'Rejected'), ('COMPLETED', 'Completed')], default='PENDING', max_length=15)),
                ('payout_created_at', models.DateTimeField(auto_now_add=True)),
                ('payout_updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.PROTECT, related_name='payout_request', to=settings.AUTH_USER_MODEL)),
                ('order_id', models.OneToOneField(db_column='order_id', on_delete=django.db.models.deletion.PROTECT, related_name='payout_request', to='base.reservationinvoice')),
            ],
            options={
                'db_table': 'payout_request',
            },
        ),
        migrations.CreateModel(
            name='SuspendedUser',
            fields=[
                ('sus_id', models.AutoField(primary_key=True, serialize=False)),
                ('sus_start', models.DateTimeField(auto_now_add=True)),
                ('sus_end', models.DateTimeField()),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('transaction_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('transaction_paypal_order_id', models.CharField(blank=True, max_length=255, null=True)),
                ('transaction_paypal_capture_id', models.CharField(blank=True, max_length=255, null=True)),
                ('transaction_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('transaction_date', models.DateTimeField(auto_now_add=True)),
                ('transaction_type', models.CharField(default='TOPUP', max_length=50)),
                ('order_id', models.ForeignKey(blank=True, db_column='invoice_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice', to='base.reservationinvoice')),
                ('user_id', models.ForeignKey(blank=True, db_column='user_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'transaction',
            },
        ),
        migrations.CreateModel(
            name='UserVerification',
            fields=[
                ('user_verification_id', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('user_verification_email', models.EmailField(max_length=254, unique=True)),
                ('user_verification_code', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('user_verification_is_verified', models.BooleanField(default=False)),
                ('user_verification_created_at', models.DateTimeField(auto_now_add=True)),
                ('user_verification_expires_at', models.DateTimeField()),
                ('user_id', models.OneToOneField(blank=True, db_column='user_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='email_verifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_verification',
            },
        ),
        migrations.CreateModel(
            name='UserApplication',
            fields=[
                ('user_id', models.OneToOneField(db_column='user_id', editable=False, on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='user_application', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('user_app_status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=10)),
                ('user_app_approved_at', models.DateTimeField(blank=True, null=True)),
                ('user_app_declined_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user_reason', models.CharField(max_length=255, null=True)),
                ('user_app_reviewer_id', models.ForeignKey(blank=True, db_column='user_app_reviewer_id', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_application',
            },
        ),
        migrations.AddConstraint(
            model_name='chatroom',
            constraint=models.UniqueConstraint(fields=('chatroom_user_1', 'chatroom_user_2'), name='unique_chat_room'),
        ),
        migrations.AlterUniqueTogether(
            name='follow',
            unique_together={('follower_id', 'following_id')},
        ),
        migrations.AlterUniqueTogether(
            name='likelog',
            unique_together={('list_id', 'user_id')},
        ),
        migrations.AlterUniqueTogether(
            name='favorite',
            unique_together={('list_id', 'user_id')},
        ),
    ]
