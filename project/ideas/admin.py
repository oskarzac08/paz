from django.contrib import admin
from .models import Idea, IdeaImage
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import UserProfile
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



# Inline for user profile to edit activation_date from User admin
class UserProfileInline(admin.StackedInline):
	model = UserProfile
	can_delete = False
	verbose_name_plural = _('profile')
	fk_name = 'user'
	readonly_fields = ('activation_date',)


class CustomUserAdmin(DefaultUserAdmin):
	inlines = (UserProfileInline,)
	list_display = DefaultUserAdmin.list_display + ('get_activation_date',)

	def get_activation_date(self, obj):
		try:
			dt = obj.profile.activation_date
			if dt:
				# format as YYYY.MM.DD HH:MM
				return dt.strftime('%Y.%m.%d %H:%M')
			return '—'
		except Exception:
			return '—'
	get_activation_date.short_description = 'Data aktywacji'
	get_activation_date.admin_order_field = 'profile__activation_date'

	# activation_date is set automatically during registration; do not allow manual setting here


# Unregister the default User admin and register the customized one
try:
	admin.site.unregister(User)
except Exception:
	pass

admin.site.register(User, CustomUserAdmin)