# /app/config.py
import sys
import os

print("Текущая директория:", os.getcwd())
print("Пути Python:", sys.path)

# Проверьте, где находится tgcloud
try:
    import tgcloud
    print("Модуль tgcloud найден по пути:", tgcloud.__file__)
    print("Содержимое tgcloud:", dir(tgcloud))
    
    # Проверьте config отдельно
    import tgcloud.config
    print("tgcloud.config найден:", tgcloud.config.__file__)
    print("Функции в tgcloud.config:", dir(tgcloud.config))
    
    # Импортируем явно
    from tgcloud.config import conf as tg_conf
    tgcloud.conf = tg_conf
    
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()
    
    # Заглушка на время отладки
    def conf_stub(config_dict):
        print(f"Заглушка: conf({config_dict})")
        return {"stub": True}
    
    tgcloud.conf = conf_stub



import tgcloud


tgcloud.__init__.conf({
 "cache_size":50,
 "trashgroup":-1002066546289,
 "tokens": [
  "7030278698:AAG2ofn_VvWVnLujhtDee6FSbQNDJl5_P2s",
  "7264787491:AAGnmEirPfrASO1Yp3cUgvTH9QH9ibK2OYc",
  "7495490897:AAF12nRjQLPCMAaybac7TJYjghGYQMcRQTo",
  "7261796926:AAGhTTxrMv_Yk-mFT8Etp4x-BeGx-NgweNU",
  "7240076335:AAGya12WpNDMS_TBuOV5kiAgM_Bo9kzypK0",
  "7208436418:AAEgGk3hacFo0AJjtSWTkMH76y0hkFb4nX8",
  "7131253048:AAEt74Jfv5NzouNy8Cj6apMEr3MAFACyLKk",
  "7267216678:AAG7Y0UkDVnCe8gPznJ5qU9jiU9lQO9w7aE",
  "7245976336:AAFESXVE-052DyssO-Eqd50B_D6zQTY4GaA"
 ],
 "groups": [
  -1002083840157,
  -1002422522816,
  -1002306580341,
  -1002282924821,
  -1002403366752,
  -1002254069821,
  -1002315855544,
  -1002496590400,
  -4716612798
 ]
})