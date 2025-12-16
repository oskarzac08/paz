// Service Catalog JavaScript - Filtrowanie i sortowanie

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search');
    const minPriceInput = document.getElementById('min_price');
    const maxPriceInput = document.getElementById('max_price');
    const sortSelect = document.getElementById('sort');
    const categoryButtons = document.querySelectorAll('.category-btn');
    const durationRadios = document.querySelectorAll('input[name="duration"]');
    const applyFiltersBtn = document.querySelector('.btn-apply-filters');
    
    // Debounce function dla wyszukiwania
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Zbieranie parametrów filtrów
    function getFilterParams() {
        const params = new URLSearchParams();
        
        // Kategoria
        const activeCategory = document.querySelector('.category-btn.active');
        if (activeCategory && activeCategory.dataset.category) {
            params.set('category', activeCategory.dataset.category);
        }
        
        // Cena
        if (minPriceInput && minPriceInput.value) {
            params.set('min_price', minPriceInput.value);
        }
        if (maxPriceInput && maxPriceInput.value) {
            params.set('max_price', maxPriceInput.value);
        }
        
        // Czas trwania
        const selectedDuration = document.querySelector('input[name="duration"]:checked');
        if (selectedDuration && selectedDuration.value) {
            params.set('duration', selectedDuration.value);
        }
        
        // Sortowanie
        if (sortSelect && sortSelect.value) {
            params.set('sort', sortSelect.value);
        }
        
        // Wyszukiwanie
        if (searchInput && searchInput.value) {
            params.set('q', searchInput.value);
        }
        
        return params;
    }
    
    // Przekierowanie z filtrami
    function applyFilters() {
        const params = getFilterParams();
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }
    
    // Obsługa kliknięcia w kategorie
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            applyFilters();
        });
    });
    
    // Obsługa zmiany sortowania
    if (sortSelect) {
        sortSelect.addEventListener('change', applyFilters);
    }
    
    // Obsługa wyszukiwania z debounce
    if (searchInput) {
        const debouncedSearch = debounce(applyFilters, 500);
        searchInput.addEventListener('input', debouncedSearch);
    }
    
    // Obsługa przycisku "Zastosuj filtry"
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    // Enter w polach cenowych
    if (minPriceInput) {
        minPriceInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') applyFilters();
        });
    }
    if (maxPriceInput) {
        maxPriceInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') applyFilters();
        });
    }
    
    // Animacja pojawiania się kart
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    entry.target.style.transition = 'opacity 0.5s, transform 0.5s';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 100);
                
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.service-card').forEach(card => {
        observer.observe(card);
    });
    
    // Lazy loading dla obrazów
    if ('loading' in HTMLImageElement.prototype) {
        // Przeglądarka wspiera native lazy loading
        const images = document.querySelectorAll('img[loading="lazy"]');
        images.forEach(img => {
            img.src = img.src;
        });
    } else {
        // Fallback dla starszych przeglądarek
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
        document.body.appendChild(script);
    }
});

// Mobile - toggle filters sidebar
function toggleFilters() {
    const sidebar = document.querySelector('.filters-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('mobile-active');
    }
}

// Responsywność - dodaj przycisk do otwierania filtrów na mobile
if (window.innerWidth <= 992) {
    const catalogMain = document.querySelector('.catalog-main');
    if (catalogMain) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'btn-toggle-filters';
        toggleBtn.innerHTML = '<i class="fas fa-filter"></i> Filtry';
        toggleBtn.onclick = toggleFilters;
        catalogMain.insertBefore(toggleBtn, catalogMain.firstChild);
    }
}

// Dodatkowe style dla mobile
const style = document.createElement('style');
style.textContent = `
    .btn-toggle-filters {
        display: none;
        width: 100%;
        padding: 0.75rem;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        font-size: 1rem;
        cursor: pointer;
        margin-bottom: 1rem;
        gap: 0.5rem;
        align-items: center;
        justify-content: center;
    }
    
    @media (max-width: 992px) {
        .btn-toggle-filters {
            display: flex;
        }
        
        .filters-sidebar {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100vh;
            z-index: 1000;
            overflow-y: auto;
        }
        
        .filters-sidebar.mobile-active {
            display: block;
        }
        
        .filters-sidebar::before {
            content: '✕';
            position: absolute;
            top: 1rem;
            right: 1rem;
            font-size: 1.5rem;
            cursor: pointer;
            z-index: 1001;
        }
    }
`;
document.head.appendChild(style);
