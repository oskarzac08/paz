from django.contrib import admin
from .models import Idea, IdeaImage


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