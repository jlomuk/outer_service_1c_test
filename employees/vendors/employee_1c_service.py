import asyncio
import logging
from dataclasses import dataclass, fields, _MISSING_TYPE, asdict
from typing import TypeVar, Tuple, NoReturn

import aiohttp
from django.conf import settings

logger = logging.getLogger('django.1c_service')
logger.setLevel(level='DEBUG')

Username = TypeVar('Username', bound=str)
Password = TypeVar('Password', bound=str)


@dataclass
class Employee:
    id: str = ''
    name: str = ''
    last_name: str = ''
    phone: str = ''
    image_url: str = ''

    def __post_init__(self):
        for field in fields(self):
            if not isinstance(field.default, _MISSING_TYPE) and getattr(self, field.name) is None:
                setattr(self, field.name, field.default)

    @classmethod
    def build_from_dict(cls, data: dict) -> list['Employee']:
        employees: list = []
        for employee in data.get('Parameters'):
            employees.append(cls(
                id=employee.get('ID', ''),
                name=employee.get('Name', ''),
                last_name=employee.get('Surname', ''),
                phone=employee.get('Phone', ''),
                image_url=employee.get('Photo', '')
            ))
        return employees


class EmployeeRequestor:
    """Простой расширяемый класс-обертка над aiohttp,
    для реализации нового запроса к сервису можно добалять методы с
    параметрами запроса и вызывать основной метод call
    """

    def __init__(self, *, user: str | None = None,
                 password: str | None = None,
                 club_id: str | None = None,
                 base_url: str | None = None, **kwargs) -> NoReturn:
        self.username = user or settings.OUTER_1C_SERVICE__USERNAME
        self.password = password or settings.OUTER_1C_SERVICE__PASSWORD
        self.club_id = club_id or settings.OUTER_1C_SERVICE__CLUB_ID
        self.base_url = base_url or settings.OUTER_1C_SERVICE__URL

    @staticmethod
    async def call(method: str, url: str, auth: None | tuple[Username, Password] = None,
                   headers: dict = None, json: dict = None, timeout: int = 5) -> dict:
        if headers is None:
            headers = {
                'Accept': 'application/json',
                'Connection': 'keep-alive',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0'
            }

        if auth:
            auth = aiohttp.BasicAuth(*auth)

        timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, auth=auth,
                                       headers=headers, json=json) as response:
                logger.info(
                    f'выполняется <{method.upper()}> запрос к {url} c параметрами: headers={headers} -- body={json}'
                )
                result = await response.json()
                return result

    async def get_employees(self) -> dict:
        body_request = {
            "Request_id": "e1477272-88d1-4acc-8e03-7008cdedc81e",
            "ClubId": self.club_id,
            "Method": "GetSpecialistList",
            "Parameters": {"ServiceId": ""}
        }
        url = self.base_url
        res = await self.call('post', url, auth=(self.username, self.password), json=body_request)
        return res


async def get_employees_from_1c_service(*args, **kwargs) -> Tuple[list[dict] | dict, int]:
    logger.info('Выполнение запроса для получения списка соотрудников к внешней системе')

    try:
        raw_data = await EmployeeRequestor(*args, **kwargs).get_employees()
    except asyncio.TimeoutError as e:
        logger.warning('Таймаут запроса, ответ не был получен от удаленного сервера 1С за отведенное время')
        return {'detail': 'Превышение времени ответа внешнего сервиса на запрос'}, 500
    except Exception as e:
        logger.error(e)
        return {'detail': 'Неизвестная ошибка'}, 500

    else:
        result = Employee.build_from_dict(raw_data)
        return [asdict(el) for el in result], 200
