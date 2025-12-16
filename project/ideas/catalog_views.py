from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Min, Max
from django.http import JsonResponse
from .models import Service, ServiceCategory


def service_catalog_view(request):
    """Katalog usług z filtrowaniem i sortowaniem"""
    
    # Pobranie parametrów filtrowania
    category_slug = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    duration = request.GET.get('duration', '')  # <30, 30-60, >60
    sort_by = request.GET.get('sort', 'order')  # order, name, price, duration, popular
    search_query = request.GET.get('q', '')
    
    # Bazowe zapytanie - tylko aktywne usługi
    services = Service.objects.filter(is_active=True).prefetch_related('images', 'category')
    
    # Filtrowanie po kategorii
    if category_slug:
        services = services.filter(category__slug=category_slug)
    
    # Filtrowanie po cenie
    if min_price:
        try:
            services = services.filter(price__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            services = services.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Filtrowanie po czasie trwania
    if duration == 'short':  # < 30 min
        services = services.filter(duration_minutes__lt=30)
    elif duration == 'medium':  # 30-60 min
        services = services.filter(duration_minutes__gte=30, duration_minutes__lte=60)
    elif duration == 'long':  # > 60 min
        services = services.filter(duration_minutes__gt=60)
    
    # Wyszukiwanie
    if search_query:
        services = services.filter(
            Q(name__icontains=search_query) |
            Q(description_short__icontains=search_query) |
            Q(description_full__icontains=search_query)
        )
    
    # Sortowanie
    if sort_by == 'name':
        services = services.order_by('name')
    elif sort_by == 'price_asc':
        services = services.order_by('price')
    elif sort_by == 'price_desc':
        services = services.order_by('-price')
    elif sort_by == 'duration':
        services = services.order_by('duration_minutes')
    elif sort_by == 'popular':
        services = services.order_by('-booking_count')
    else:  # order (domyślne)
        services = services.order_by('order', 'name')
    
    # Kategorie (dla menu filtrów)
    categories = ServiceCategory.objects.filter(
        is_active=True,
        services__is_active=True
    ).distinct().annotate(
        service_count=Count('services')
    ).order_by('order', 'name')
    
    # Statystyki dla filtrów cenowych
    price_stats = Service.objects.filter(is_active=True).aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    context = {
        'services': services,
        'categories': categories,
        'selected_category': category_slug,
        'price_stats': price_stats,
        'current_filters': {
            'category': category_slug,
            'min_price': min_price,
            'max_price': max_price,
            'duration': duration,
            'sort': sort_by,
            'search': search_query,
        },
        'result_count': services.count(),
    }
    
    return render(request, 'ideas/service_catalog.html', context)


def service_detail_view(request, service_id):
    """Szczegóły pojedynczej usługi"""
    service = get_object_or_404(
        Service.objects.prefetch_related('images'),
        pk=service_id,
        is_active=True
    )
    
    # Podobne usługi (ta sama kategoria)
    related_services = Service.objects.filter(
        is_active=True,
        category=service.category
    ).exclude(pk=service_id).prefetch_related('images')[:3]
    
    context = {
        'service': service,
        'related_services': related_services,
        'primary_image': service.primary_image,
        'gallery_images': service.gallery_images,
    }
    
    return render(request, 'ideas/service_detail.html', context)


def service_api_list(request):
    """API endpoint dla dynamicznego ładowania usług (AJAX)"""
    category_slug = request.GET.get('category', '')
    
    services = Service.objects.filter(is_active=True)
    
    if category_slug:
        services = services.filter(category__slug=category_slug)
    
    services = services.prefetch_related('images').order_by('order', 'name')
    
    data = []
    for service in services:
        primary_img = service.primary_image
        data.append({
            'id': service.id,
            'name': service.name,
            'description_short': service.description_short,
            'price': float(service.price),
            'duration_minutes': service.duration_minutes,
            'color': service.color,
            'icon': service.icon,
            'image_url': primary_img.image.url if primary_img else None,
            'detail_url': f'/services/{service.id}/',
            'booking_url': f'/booking/service/?service_id={service.id}',
        })
    
    return JsonResponse({'services': data})
