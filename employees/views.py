import logging

from django.core.cache import cache
from django.http import JsonResponse

from employees.vendors.employee_1c_service import get_employees_from_1c_service

logger = logging.getLogger('django.views')


async def get_employees(request, *args, **kwargs):
    if data := cache.get('employees_get'):
        logger.info("Данные найдены в кеше")
        result, status_code = data
    else:
        result, status_code = await get_employees_from_1c_service()
        if status_code == 200:
            cache.set('employees_get', (result, status_code), 60 * 2)
    return JsonResponse(result, status=status_code, safe=False)
