from django.contrib import admin
from .models import Idea, IdeaImage, UserProfile, ActivationCode
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class IdeaImageInline(admin.TabularInline):
	model = IdeaImage
	extra = 1
	readonly_fields = ('uploaded_at', 'uploaded_by')


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
	list_display = ('id', 'title', 'created_at', 'updated_at', 'author')
	search_fields = ('title', 'description')
	readonly_fields = ('created_at', 'updated_at')
	inlines = [IdeaImageInline]
	exclude = ('author',)
    
	def save_formset(self, request, form, formset, change):
		instances = formset.save(commit=False)
		# set uploaded_by for new/unspecified images and save instances
		for instance in instances:
			if isinstance(instance, IdeaImage) and not instance.uploaded_by:
				instance.uploaded_by = request.user
			instance.save()

		# handle deleted objects from the formset
		if hasattr(formset, 'deleted_objects'):
			for obj in formset.deleted_objects:
				obj.delete()

		formset.save_m2m()
    
	def save_model(self, request, obj, form, change):
		# On create, set the author to the current user automatically
		if not change or not obj.author:
			obj.author = request.user
		super().save_model(request, obj, form, change)


# Inline for user profile
class UserProfileInline(admin.StackedInline):
	model = UserProfile
	can_delete = False
	verbose_name_plural = _('Profil użytkownika')
	fk_name = 'user'
	fields = ('phone_number', 'preferred_contact', 'email_verified', 'phone_verified', 'activation_date')
	readonly_fields = ('activation_date',)


class CustomUserAdmin(DefaultUserAdmin):
	inlines = (UserProfileInline,)
	list_display = DefaultUserAdmin.list_display + ('get_activation_date', 'get_email_verified', 'get_phone_verified')

	def get_activation_date(self, obj):
		try:
			dt = obj.profile.activation_date
			if dt:
				return dt.strftime('%Y.%m.%d %H:%M')
			return '—'
		except Exception:
			return '—'
	get_activation_date.short_description = 'Data aktywacji'
	get_activation_date.admin_order_field = 'profile__activation_date'

	def get_email_verified(self, obj):
		try:
			return obj.profile.email_verified
		except:
			return False
	get_email_verified.short_description = 'E-mail zweryfikowany'
	get_email_verified.boolean = True

	def get_phone_verified(self, obj):
		try:
			return obj.profile.phone_verified
		except:
			return False
	get_phone_verified.short_description = 'Telefon zweryfikowany'
	get_phone_verified.boolean = True


@admin.register(ActivationCode)
class ActivationCodeAdmin(admin.ModelAdmin):
	list_display = ('user', 'code', 'channel', 'created_at', 'expires_at', 'is_used', 'get_is_valid')
	list_filter = ('channel', 'is_used', 'created_at')
	search_fields = ('user__username', 'user__email', 'code')
	readonly_fields = ('created_at', 'used_at', 'get_is_valid', 'get_is_expired')
	
	def get_is_valid(self, obj):
		return obj.is_valid
	get_is_valid.boolean = True
	get_is_valid.short_description = 'Czy ważny'
	
	def get_is_expired(self, obj):
		return obj.is_expired
	get_is_expired.boolean = True
	get_is_expired.short_description = 'Czy wygasł'


# Unregister the default User admin and register the customized one
try:
	admin.site.unregister(User)
except Exception:
	pass

admin.site.register(User, CustomUserAdmin)
