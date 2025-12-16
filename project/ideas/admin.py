from django.contrib import admin
from .models import Idea, IdeaImage, UserProfile, ActivationCode
from .models import Service, ServiceImage, ServiceCategory, Reservation, TimeSlot, RecurringSlotTemplate
from .models import Notification, NotificationPreference, ReservationNote
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.utils.html import format_html


class IdeaImageInline(admin.TabularInline):
	model = IdeaImage
	extra = 1
	readonly_fields = ('uploaded_at', 'uploaded_by')


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
	list_display = ('id', 'title', 'author', 'created_at', 'updated_at')
	list_display_links = ('id', 'title')
	search_fields = ('title', 'description', 'author__username')
	list_filter = ('created_at', 'author')
	readonly_fields = ('created_at', 'updated_at', 'author')
	inlines = [IdeaImageInline]
	date_hierarchy = 'created_at'
	list_per_page = 25
    
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
	fields = ('phone_number', 'preferred_contact', 'email_verified', 'phone_verified', 'activation_date', 'customer_segment', 'total_visits', 'total_spent', 'last_visit_date', 'favorite_service')
	readonly_fields = ('activation_date', 'customer_segment', 'total_visits', 'total_spent', 'last_visit_date', 'favorite_service')


# Inline dla rezerwacji użytkownika
class UserReservationInline(admin.TabularInline):
	model = Reservation
	fk_name = 'user'
	extra = 0
	can_delete = False
	verbose_name_plural = _('Historia rezerwacji')
	fields = ('start', 'service', 'status', 'customer_email', 'customer_phone', 'view_details')
	readonly_fields = ('start', 'service', 'status', 'customer_email', 'customer_phone', 'view_details')
	ordering = ('-start',)
	
	def has_add_permission(self, request, obj=None):
		return False
	
	def view_details(self, obj):
		"""Link do szczegółów rezerwacji"""
		from django.urls import reverse
		url = reverse('admin:ideas_reservation_change', args=[obj.id])
		return format_html(
			'<a href="{}" target="_blank">Szczegóły</a>',
			url
		)
	view_details.short_description = 'Akcje'


class CustomUserAdmin(DefaultUserAdmin):
	inlines = (UserProfileInline, UserReservationInline)
	list_display = DefaultUserAdmin.list_display + ('get_activation_date', 'get_email_verified', 'get_phone_verified', 'view_client_profile')

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
	
	def view_client_profile(self, obj):
		"""Link do pełnego profilu klienta z historią"""
		from django.urls import reverse
		url = reverse('ideas:staff_client_profile', args=[obj.id])
		return format_html(
			'<a href="{}" class="button" target="_blank">📊 Historia</a>',
			url
		)
	view_client_profile.short_description = 'Profil klienta'


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


# Service Image Inline
class ServiceImageInline(admin.TabularInline):
	model = ServiceImage
	extra = 1
	fields = ('image', 'alt_text', 'is_primary', 'order', 'uploaded_at')
	readonly_fields = ('uploaded_at',)
	max_num = 6  # Maksymalnie 6 zdjęć według PDR-005


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'slug', 'order', 'is_active', 'service_count')
	list_display_links = ('id', 'name')
	list_filter = ('is_active',)
	search_fields = ('name', 'description')
	prepopulated_fields = {'slug': ('name',)}
	list_editable = ('order', 'is_active')
	list_per_page = 25
	
	def service_count(self, obj):
		return obj.services.filter(is_active=True).count()
	service_count.short_description = 'Aktywnych usług'


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
	list_display = (
		'id', 'name', 'category', 'duration_minutes', 'price', 
		'color_preview', 'icon_preview', 'is_active', 'order', 'booking_count'
	)
	list_display_links = ('id', 'name')
	search_fields = ('name', 'description', 'description_short', 'description_full')
	list_filter = ('is_active', 'category', 'duration_minutes')
	list_editable = ('order', 'is_active')
	inlines = [ServiceImageInline]
	fieldsets = (
		('Podstawowe informacje', {
			'fields': ('name', 'category', 'description_short', 'description_full', 'description')
		}),
		('Parametry usługi', {
			'fields': ('duration_minutes', 'price')
		}),
		('Wizualizacja', {
			'fields': ('color', 'icon'),
			'description': 'Kolor w formacie HEX (np. #FF5733), Ikona z FontAwesome (np. fa-cut)'
		}),
		('Status i kolejność', {
			'fields': ('is_active', 'order')
		}),
		('Statystyki', {
			'fields': ('booking_count', 'created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	readonly_fields = ('booking_count', 'created_at', 'updated_at')
	list_per_page = 25
	
	def color_preview(self, obj):
		"""Podgląd koloru"""
		return format_html(
			'<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
			obj.color
		)
	color_preview.short_description = 'Kolor'
	
	def icon_preview(self, obj):
		"""Podgląd ikony"""
		if obj.icon:
			# Obsługa FontAwesome
			if obj.icon.startswith('fa-'):
				return format_html('<i class="fas {}"></i> {}', obj.icon, obj.icon)
			# Obsługa Material Icons
			return format_html('<span class="material-icons">{}</span> {}', obj.icon, obj.icon)
		return '-'
	icon_preview.short_description = 'Ikona'
	
	def save_formset(self, request, form, formset, change):
		"""Auto-ustawia uploaded_by dla nowych zdjęć"""
		instances = formset.save(commit=False)
		for instance in instances:
			if isinstance(instance, ServiceImage) and not instance.uploaded_by:
				instance.uploaded_by = request.user
			instance.save()
		
		if hasattr(formset, 'deleted_objects'):
			for obj in formset.deleted_objects:
				obj.delete()
		
		formset.save_m2m()


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
	list_display = ('id', 'service', 'image_preview', 'is_primary', 'order', 'uploaded_at', 'uploaded_by')
	list_display_links = ('id', 'service')
	list_filter = ('is_primary', 'service', 'uploaded_at')
	search_fields = ('service__name', 'alt_text')
	list_editable = ('is_primary', 'order')
	readonly_fields = ('uploaded_at', 'image_preview_large')
	fields = ('service', 'image', 'image_preview_large', 'alt_text', 'is_primary', 'order', 'uploaded_by', 'uploaded_at')
	list_per_page = 50
	
	def image_preview(self, obj):
		"""Miniatura zdjęcia w liście"""
		if obj.image:
			return format_html(
				'<img src="{}" style="width: 50px; height: auto; max-height: 50px;" />',
				obj.image.url
			)
		return '-'
	image_preview.short_description = 'Podgląd'
	
	def image_preview_large(self, obj):
		"""Większy podgląd zdjęcia w formularzu"""
		if obj.image:
			return format_html(
				'<img src="{}" style="max-width: 400px; max-height: 400px;" />',
				obj.image.url
			)
		return '-'
	image_preview_large.short_description = 'Podgląd zdjęcia'


# ReservationNote Inline (PDR-008)
class ReservationNoteInline(admin.TabularInline):
	"""Inline dla notatek obsługi do rezerwacji"""
	model = ReservationNote
	extra = 0
	fields = ('note', 'is_important', 'author', 'created_at')
	readonly_fields = ('author', 'created_at')
	can_delete = False  # Notatki nie powinny być usuwane dla zachowania historii
	
	def has_add_permission(self, request, obj=None):
		# Tylko staff może dodawać notatki
		return request.user.is_staff
	
	def has_change_permission(self, request, obj=None):
		# Notatki nie powinny być edytowane po utworzeniu
		return False
	
	def save_model(self, request, obj, form, change):
		if not obj.author:
			obj.author = request.user
		super().save_model(request, obj, form, change)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
	list_display = (
		'id', 'get_customer_name', 'service', 'start', 'status', 
		'cancelled_by_staff', 'customer_email', 'customer_phone', 'view_client_profile'
	)
	list_display_links = ('id', 'get_customer_name')
	list_filter = ('status', 'service', 'is_guest', 'cancelled_by_staff', 'created_at')
	search_fields = (
		'customer_email', 'customer_first_name', 'customer_last_name', 
		'customer_phone', 'confirmation_code'
	)
	date_hierarchy = 'start'
	readonly_fields = (
		'created_at', 'updated_at', 'cancelled_at', 'cancelled_by', 
		'cancellation_token_expires', 'get_hours_until', 'get_can_cancel'
	)
	fieldsets = (
		('Informacje podstawowe', {
			'fields': ('service', 'user', 'status')
		}),
		('Dane klienta', {
			'fields': (
				'customer_first_name', 'customer_last_name', 
				'customer_email', 'customer_phone', 'is_guest'
			)
		}),
		('Szczegóły rezerwacji', {
			'fields': ('start', 'end', 'notes', 'confirmation_code')
		}),
		('Informacje o odwołaniu', {
			'fields': (
				'cancelled_at', 'cancelled_by', 'cancelled_by_staff',
				'cancellation_reason', 'cancellation_note',
				'cancellation_token', 'cancellation_token_expires'
			),
			'classes': ('collapse',)
		}),
		('Metadata', {
			'fields': ('created_at', 'updated_at', 'get_hours_until', 'get_can_cancel'),
			'classes': ('collapse',)
		}),
	)
	list_per_page = 25
	actions = ['cancel_reservations', 'mark_as_completed', 'mark_as_no_show']
	inlines = [ReservationNoteInline]  # PDR-008: Notatki obsługi
	
	def get_customer_name(self, obj):
		if obj.customer_first_name or obj.customer_last_name:
			return f"{obj.customer_first_name} {obj.customer_last_name}".strip()
		return obj.customer_email
	get_customer_name.short_description = 'Klient'
	get_customer_name.admin_order_field = 'customer_last_name'
	
	def get_hours_until(self, obj):
		if not obj.start:
			return "-"
		hours = obj.hours_until_appointment
		if hours > 0:
			return f"{hours:.1f} godz."
		return "Minęło"
	get_hours_until.short_description = 'Do wizyty'
	
	def get_can_cancel(self, obj):
		if not obj.start:
			return False
		can_cancel, message = obj.can_cancel(by_staff=True)
		return can_cancel
	get_can_cancel.boolean = True
	get_can_cancel.short_description = 'Można odwołać'
	
	def view_client_profile(self, obj):
		"""Link do profilu klienta z historią"""
		if obj.user:
			from django.urls import reverse
			url = reverse('ideas:staff_client_profile', args=[obj.user.id])
			return format_html(
				'<a href="{}" class="button" target="_blank">📊</a>',
				url
			)
		return '-'
	view_client_profile.short_description = 'Profil'
	
	def cancel_reservations(self, request, queryset):
		"""Akcja masowego odwoływania wizyt przez obsługę"""
		cancelled_count = 0
		for reservation in queryset:
			can_cancel, _ = reservation.can_cancel(by_staff=True)
			if can_cancel:
				try:
					reservation.cancel(
						cancelled_by=request.user,
						by_staff=True,
						reason='staff_cancelled',
						note=f'Odwołane przez {request.user.get_full_name() or request.user.username} z panelu admin'
					)
					cancelled_count += 1
				except Exception:
					pass
		
		self.message_user(request, f'Odwołano {cancelled_count} wizyt.')
	cancel_reservations.short_description = 'Odwołaj wybrane wizyty (obsługa)'
	
	def mark_as_completed(self, request, queryset):
		"""Akcja oznaczania wizyt jako zrealizowane"""
		updated = queryset.filter(
			status__in=['pending', 'confirmed']
		).update(status='completed')
		self.message_user(request, f'Oznaczono {updated} wizyt jako zrealizowane.')
	mark_as_completed.short_description = 'Oznacz jako zrealizowane'
	
	def mark_as_no_show(self, request, queryset):
		"""Akcja oznaczania wizyt jako nieobecność"""
		updated = queryset.filter(
			status__in=['pending', 'confirmed']
		).update(status='no_show')
		self.message_user(request, f'Oznaczono {updated} wizyt jako nieobecność.')
	mark_as_no_show.short_description = 'Oznacz jako nieobecność (no-show)'


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
	list_display = ('id', 'service', 'start', 'end', 'get_duration', 'status', 'is_recurring', 'created_at')
	list_display_links = ('id', 'service')
	list_filter = ('service', 'status', 'is_recurring', 'created_at', 'start')
	date_hierarchy = 'start'
	search_fields = ('service__name', 'block_note', 'recurring_group_id')
	readonly_fields = ('created_at', 'duration_minutes', 'is_available', 'is_past')
	list_per_page = 50
	ordering = ('-start',)
	
	fieldsets = (
		('Podstawowe informacje', {
			'fields': ('service', 'start', 'end', 'status')
		}),
		('Blokada', {
			'fields': ('block_reason', 'block_note'),
			'classes': ('collapse',)
		}),
		('Cykliczność', {
			'fields': ('is_recurring', 'recurring_group_id', 'template'),
			'classes': ('collapse',)
		}),
		('Metadane', {
			'fields': ('created_by', 'created_at', 'duration_minutes', 'is_available', 'is_past'),
			'classes': ('collapse',)
		}),
	)
	
	actions = ['block_slots_action', 'unblock_slots_action', 'delete_available_slots']
	
	def get_duration(self, obj):
		return f"{obj.duration_minutes} min"
	get_duration.short_description = 'Czas trwania'
	
	def block_slots_action(self, request, queryset):
		"""Blokuj wybrane sloty"""
		available_slots = queryset.filter(status='available')
		count = 0
		for slot in available_slots:
			try:
				slot.block(reason='other', note='Zablokowane przez admina', blocked_by=request.user)
				count += 1
			except:
				pass
		self.message_user(request, f'Zablokowano {count} slotów.')
	block_slots_action.short_description = 'Zablokuj wybrane sloty'
	
	def unblock_slots_action(self, request, queryset):
		"""Odblokuj wybrane sloty"""
		blocked_slots = queryset.filter(status='blocked')
		count = 0
		for slot in blocked_slots:
			try:
				slot.unblock()
				count += 1
			except:
				pass
		self.message_user(request, f'Odblokowano {count} slotów.')
	unblock_slots_action.short_description = 'Odblokuj wybrane sloty'
	
	def delete_available_slots(self, request, queryset):
		"""Usuń tylko dostępne sloty (bez rezerwacji)"""
		available = queryset.filter(status='available')
		count, _ = available.delete()
		self.message_user(request, f'Usunięto {count} dostępnych slotów.')
	delete_available_slots.short_description = 'Usuń dostępne sloty'
	
	def save_model(self, request, obj, form, change):
		if not change or not obj.created_by:
			obj.created_by = request.user
		super().save_model(request, obj, form, change)


@admin.register(RecurringSlotTemplate)
class RecurringSlotTemplateAdmin(admin.ModelAdmin):
	list_display = ('name', 'service', 'get_days', 'get_hours', 'slot_interval_minutes', 'is_active', 'created_at')
	list_filter = ('service', 'is_active', 'created_at')
	search_fields = ('name', 'description', 'service__name')
	readonly_fields = ('created_at', 'updated_at', 'active_days')
	list_per_page = 25
	
	fieldsets = (
		('Podstawowe informacje', {
			'fields': ('name', 'description', 'service', 'is_active')
		}),
		('Dni tygodnia', {
			'fields': ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
		}),
		('Godziny i interwały', {
			'fields': ('start_time', 'end_time', 'slot_interval_minutes')
		}),
		('Przerwy', {
			'fields': ('breaks',),
			'description': 'Lista przerw w formacie JSON'
		}),
		('Metadane', {
			'fields': ('created_by', 'created_at', 'updated_at', 'active_days'),
			'classes': ('collapse',)
		}),
	)
	
	actions = ['apply_template_action']
	
	def get_days(self, obj):
		return ', '.join(obj.active_days)
	get_days.short_description = 'Dni tygodnia'
	
	def get_hours(self, obj):
		return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
	get_hours.short_description = 'Godziny'
	
	def save_model(self, request, obj, form, change):
		if not change or not obj.created_by:
			obj.created_by = request.user
		super().save_model(request, obj, form, change)


# ============================================
# NOTIFICATION ADMIN
# ============================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	"""Admin panel dla powiadomień"""
	list_display = ('id', 'user_display', 'notification_type', 'channel', 'status', 'recipient', 'created_at', 'sent_at')
	list_filter = ('status', 'channel', 'notification_type', 'created_at')
	search_fields = ('recipient', 'user__username', 'user__email', 'subject', 'message')
	readonly_fields = ('created_at', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at')
	date_hierarchy = 'created_at'
	list_per_page = 50
	
	fieldsets = (
		('Podstawowe informacje', {
			'fields': ('user', 'notification_type', 'channel', 'status')
		}),
		('Odbiorca i treść', {
			'fields': ('recipient', 'subject', 'message', 'html_message')
		}),
		('Status i błędy', {
			'fields': ('error_message', 'retry_count')
		}),
		('Powiązanie', {
			'fields': ('related_object_type', 'related_object_id'),
			'classes': ('collapse',)
		}),
		('Timestamps', {
			'fields': ('created_at', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at'),
			'classes': ('collapse',)
		}),
	)
	
	def user_display(self, obj):
		"""Wyświetla użytkownika z linkiem"""
		if obj.user:
			return format_html(
				'<a href="/admin/auth/user/{}/change/">{}</a>',
				obj.user.id,
				obj.user.get_full_name() or obj.user.username
			)
		return '-'
	user_display.short_description = 'Użytkownik'
	
	actions = ['resend_notification', 'mark_as_sent', 'mark_as_failed']
	
	def resend_notification(self, request, queryset):
		"""Ponowne wysłanie powiadomienia"""
		from .notification_tasks import send_notification_task
		
		count = 0
		for notification in queryset:
			if notification.status in ['failed', 'pending']:
				notification.status = 'pending'
				notification.retry_count = 0
				notification.error_message = ''
				notification.save()
				
				# Wyślij asynchronicznie
				send_notification_task.delay(notification.id)
				count += 1
		
		self.message_user(request, f'Ponownie wysłano {count} powiadomień.')
	resend_notification.short_description = 'Wyślij ponownie'
	
	def mark_as_sent(self, request, queryset):
		"""Oznacz jako wysłane"""
		updated = queryset.update(status='sent')
		self.message_user(request, f'Zaktualizowano {updated} powiadomień.')
	mark_as_sent.short_description = 'Oznacz jako wysłane'
	
	def mark_as_failed(self, request, queryset):
		"""Oznacz jako nieudane"""
		updated = queryset.update(status='failed')
		self.message_user(request, f'Zaktualizowano {updated} powiadomień.')
	mark_as_failed.short_description = 'Oznacz jako nieudane'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
	"""Admin panel dla preferencji powiadomień"""
	list_display = ('user', 'preferred_channel', 'enable_reminder_24h', 'enable_reminder_2h', 'enable_marketing', 'updated_at')
	list_filter = ('preferred_channel', 'enable_reminder_24h', 'enable_reminder_2h', 'enable_marketing')
	search_fields = ('user__username', 'user__email')
	readonly_fields = ('created_at', 'updated_at')
	
	fieldsets = (
		('Użytkownik', {
			'fields': ('user',)
		}),
		('Preferowany kanał', {
			'fields': ('preferred_channel',)
		}),
		('Powiadomienia transakcyjne', {
			'fields': ('enable_booking_confirmation', 'enable_booking_cancellation'),
			'description': 'Te powiadomienia nie mogą być wyłączone.'
		}),
		('Przypomnienia', {
			'fields': ('enable_reminder_24h', 'enable_reminder_2h')
		}),
		('Zmiany i aktualizacje', {
			'fields': ('enable_booking_changes',)
		}),
		('Marketing', {
			'fields': ('enable_marketing', 'enable_newsletter')
		}),
		('Godziny ciszy', {
			'fields': ('quiet_hours_start', 'quiet_hours_end'),
			'classes': ('collapse',)
		}),
		('Metadata', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)


@admin.register(ReservationNote)
class ReservationNoteAdmin(admin.ModelAdmin):
	"""Admin panel dla notatek obsługi (PDR-008)"""
	list_display = ('id', 'reservation_display', 'customer_display', 'note_preview', 'is_important', 'author', 'created_at')
	list_display_links = ('id', 'note_preview')
	list_filter = ('is_important', 'created_at', 'author')
	search_fields = (
		'note', 
		'reservation__customer_first_name', 
		'reservation__customer_last_name',
		'reservation__customer_email',
		'author__username'
	)
	date_hierarchy = 'created_at'
	readonly_fields = ('created_at', 'author', 'reservation')
	list_per_page = 50
	
	fieldsets = (
		('Notatka', {
			'fields': ('reservation', 'note', 'is_important')
		}),
		('Metadata', {
			'fields': ('author', 'created_at'),
			'classes': ('collapse',)
		}),
	)
	
	def reservation_display(self, obj):
		"""Wyświetla rezerwację z linkiem"""
		return format_html(
			'<a href="/admin/ideas/reservation/{}/change/">#{} - {}</a>',
			obj.reservation.id,
			obj.reservation.id,
			obj.reservation.service.name
		)
	reservation_display.short_description = 'Rezerwacja'
	
	def customer_display(self, obj):
		"""Wyświetla klienta"""
		return obj.reservation.get_customer_name()
	customer_display.short_description = 'Klient'
	customer_display.admin_order_field = 'reservation__customer_last_name'
	
	def note_preview(self, obj):
		"""Skrócony podgląd notatki"""
		if len(obj.note) > 50:
			return obj.note[:50] + '...'
		return obj.note
	note_preview.short_description = 'Treść notatki'
	
	def has_delete_permission(self, request, obj=None):
		# Notatki nie powinny być usuwane dla zachowania historii
		return False
	
	def has_change_permission(self, request, obj=None):
		# Notatki nie powinny być edytowane po utworzeniu
		return False
	
	def save_model(self, request, obj, form, change):
		"""Automatycznie przypisz autora"""
		if not obj.author:
			obj.author = request.user
		super().save_model(request, obj, form, change)
