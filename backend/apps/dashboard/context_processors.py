from apps.sites.models import Site
from apps.alarms.models import AlarmEvent
from django.db.models import Count

def global_dashboard_stats(request):
    if not request.user.is_authenticated:
        return {}
    
    # Sites for Command Palette Search
    # We prefetch devices to determine online status efficiently
    sites_qs = Site.objects.all().prefetch_related("devices")
    
    sites_data = []
    online_count = 0
    offline_count = 0
    operational_count = 0
    blocked_count = 0

    for site in sites_qs:
        is_online = any(d.is_online for d in site.devices.all())
        if is_online: online_count += 1
        else: offline_count += 1
        
        if site.is_active: operational_count += 1
        else: blocked_count += 1

        sites_data.append({
            'id': str(site.id),
            'name': site.name,
            'hik_site_id': site.hik_site_id,
            'is_active': site.is_active,
            'is_online': is_online
        })
    
    # Recent Events for HUD Ticker
    recent_events = AlarmEvent.objects.select_related('site').order_by('-occurred_at')[:5]
    
    # Global Health Percentage (Online Reach)
    total_sites = sites_qs.count()
    health_percentage = round((online_count / total_sites * 100)) if total_sites > 0 else 100

    return {
        'global_sites': sites_data,
        'global_config': {
            'tickerCount': recent_events.count(),
            'health': health_percentage,
        },
        'global_recent_events': recent_events,
        'global_health_percentage': health_percentage,
        'global_counts': {
            'online': online_count,
            'offline': offline_count,
            'operational': operational_count,
            'blocked': blocked_count
        }
    }
