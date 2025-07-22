# scraper.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
import os
import re

# --- Django Ortamını Yükle ---
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kiraradar.settings') # Doğru proje adı: kiraradar
django.setup()

# Modellerinizi import edin
from emlak.models import Bolge, KiraIlani
from datetime import date

# ChromeDriver'ın yolu (projenin ana dizininde olduğu için sadece dosya adı yeterli)
CHROME_DRIVER_PATH = './chromedriver.exe'

# Emlakjet'in İstanbul, Kadıköy, Kiralık Konutlar sayfası
URL = "https://www.emlakjet.com/kiralik-konut/istanbul-kadikoy/"

# Chrome seçeneklerini ayarla
chrome_options = Options()
chrome_options.add_argument("--headless") # *** Önemli Değişiklik: Headless modu açıldı ***
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
chrome_options.add_argument("--window-size=1920,1080") # Headless modda da ekran boyutunu ayarla
chrome_options.add_argument("--disable-blink-features=AutomationControlled") # Yeni anti-bot önlemi

# Anti-bot argümanları (daha agresif)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
# Bu satır en kritik olanlardan biri olabilir
# chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process") # Bazı durumlarda faydalı olabilir, şimdilik denemeyelim.

service = Service(CHROME_DRIVER_PATH)
driver = None

def parse_price(price_str):
    """Fiyat stringini sayıya dönüştürür."""
    try:
        cleaned_price = re.sub(r'[^\d]', '', price_str)
        return int(cleaned_price)
    except ValueError:
        return None

def parse_location(location_str):
    """Konum stringinden il, ilçe, mahalle ayıklar."""
    sehir = "İstanbul" # Şimdilik sabit tutalım
    ilce = None
    mahalle = None

    parts = [p.strip() for p in re.split(r'[-–]', location_str)]
    
    if len(parts) >= 2:
        ilce_candidate = parts[0].strip()
        mahalle_candidate = parts[1].strip()
        
        if "Mahallesi" in ilce_candidate:
            ilce_parts = ilce_candidate.split()
            if len(ilce_parts) > 1:
                ilce = ilce_parts[0]
                mahalle = ' '.join(ilce_parts[1:]).replace("Mahallesi", "").strip()
            else:
                ilce = ilce_candidate.replace("Mahallesi", "").strip()
        else:
            ilce = ilce_candidate
            mahalle = mahalle_candidate.replace("Mahallesi", "").strip()

    elif len(parts) == 1:
        location_parts = location_str.split()
        if len(location_parts) > 0:
            ilce = location_parts[0].strip()
            if len(location_parts) > 1:
                mahalle_temp = ' '.join(location_parts[1:]).strip()
                mahalle = mahalle_temp.replace("Mahallesi", "").strip()
            
    if not mahalle:
        mahalle = None
    
    if not ilce and len(location_str.split()) > 0:
        ilce = location_str.split()[0].strip()

    if not sehir: sehir = "İstanbul"
    if not ilce: ilce = "Kadıköy" # Varsayılan ilçe
    if mahalle == "": mahalle = None

    return sehir, ilce, mahalle

try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("Chrome tarayıcısı başlatıldı.")

    # *** Önemli Değişiklik: navigator.webdriver'ı devre dışı bırak ***
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    driver.get(URL)
    print(f"URL'ye gidildi: {URL}")

    # Önemli Değişiklik: Daha uzun bekleme süresi ve visibility_of_element_located
    try:
        # Daha genel bir element bekleyebiliriz, örneğin ilanları içeren ana container
        # HTML çıktınızda ilanları listeleyen ana div'i bulmaya çalışalım.
        # Genellikle bu tarz listelemelerde "styles_listingPanel__" gibi bir şey olur.
        # HTML çıktınızda şu kısım vardı:
        # <div class="styles_container__ckpa5"><div class="styles_breadcrumbWrapper__5LJhp">...</div><div class="styles_wrapper__lxn6A"><div class="styles_titleContainer__qbewu"><div class="styles_mainTitle__boK5Y"><h1 class="styles_title__
        # Belki 'styles_wrapper__lxn6A' içindeki content yüklenmesini bekleyebiliriz.
        
        # En kesin yol, tarayıcıda F12 ile inceleyip ilanları listeleyen div'in ID veya sınıfını bulmak.
        # Geçici olarak, Emlakjet'in "ilan listesi"ni içeren ana container'ının class'ı 'styles_listingPanel__...' olabilir.
        # Veya "styles_wrapper__lxn6A" bu sefer dolu gelirse onu kullanırız.

        # Şimdilik, ilan kartlarının direkt kendisini bekleyelim. Eğer hata alırsak bu seçiciyi değiştireceğiz.
        # Tarayıcıyı açtığınızda ilanların ana kapsayıcı div'inin veya doğrudan bir ilan kartının sınıfını kontrol edin.
        # Varsayılan olarak şu anki '.list-card' seçiciniz doğruysa bunu beklemeye devam edelim.
        
        # EMLAKJET YENİ HTML YAPISI DİKKAT:
        # Emlakjet son zamanlarda ilanları styles_listCard__... gibi bir div içinde barındırıyor.
        # Eğer '.list-card' çalışmazsa, bunu 'div.styles_listCardWrapper__...' veya benzeri bir şeye değiştirmemiz gerekebilir.
        
        # Deneyelim: Yeni Emlakjet HTML yapısına göre 'styles_listCard__...' sınıfına sahip elementlerden birinin yüklenmesini bekleyelim.
        # Bu sınıf, ilanların ana kartının bir parçasıdır.
        # Eğer bu element yüklenmiyorsa, sayfanın içeriği gelmiyordur.
        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "a.styles_listCard__2LgYJ")) # Bu sınıfı deneyelim
            # Alternatif olarak: (By.CSS_SELECTOR, "div.styles_listCardWrapper__Z8R6S")
            # Ya da: (By.XPATH, "//a[contains(@class, 'list-card') or contains(@class, 'styles_listCard__')]")
        )
        print("İlan içeriği yüklendiği algılandı (Emlakjet).")
        time.sleep(5) # Sayfanın tamamen stabil hale gelmesi için ek bekleme süresi

        # Sayfayı aşağı kaydırarak tüm ilanların yüklenmesini sağlama
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 5 # Çok fazla kaydırmayı engellemek için limit
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) # Kaydırdıktan sonra yeni ilanların yüklenmesini bekle
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height or scroll_attempts >= max_scroll_attempts:
                break # Sayfa daha fazla kaymıyorsa veya maksimum denemeye ulaştıysak dur
            last_height = new_height
            scroll_attempts += 1
        print("Sayfa sonuna kadar kaydırıldı veya maksimum kaydırma denemesine ulaşıldı.")
        time.sleep(3) # Son kaydırmadan sonra son ilanların yüklenmesi için ek bekleme

    except TimeoutException:
        print("Emlakjet sayfasında ilanların yüklenmesi beklenenden uzun sürdü (Timeout).")
        with open("emlakjet_timeout_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Mevcut sayfa kaynağı 'emlakjet_timeout_page_source.html' dosyasına kaydedildi.")
        pass

    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')

    current_title = soup.title.string.strip() if soup.title else "Başlık Yok"
    print(f"Güncel Sayfa Başlığı: {current_title}")

    # Yeni Emlakjet HTML yapısına göre ilanları bulalım
    # Önemli: Emlakjet'te ilanlar genellikle <a class="styles_listCard__..." href="..."> yapısıyla gelir.
    # Bu nedenle, 'a' etiketi ve doğru sınıfı hedeflememiz gerekiyor.
    # Bu sınıf adı değişebilir, bu yüzden lütfen manuel olarak bir ilanın HTML'ini kontrol edin.
    
    # Geçici olarak bilinen bir sınıfı kullanıyorum. HTML'de bulamazsak değiştireceğiz.
    listings = soup.find_all('a', class_='styles_listCard__2LgYJ') # Bu seçiciyi kullandık

    if not listings:
        print("Emlakjet'te hiç ilan bulunamadı. Lütfen HTML elementlerini kontrol edin veya bekleme süresini artırın.")
        # Bu noktada, eğer hala ilan bulunamıyorsa, 'emlakjet_timeout_page_source.html' dosyasını tekrar kontrol etmeliyiz.
        # Sayfayı kendiniz açtığınızda bir ilanın HTML yapısından örnek alıp o seçiciyi buraya girmemiz gerekebilir.
    else:
        print(f"\nSayfadan bulunan toplam {len(listings)} ilan bilgisi.")
        for i, listing in enumerate(listings):
            try:
                # İlan başlığı
                # title_element = listing.find('div', class_='realty-name') # Eski
                title_element = listing.find('div', class_=re.compile(r'styles_realtyName__')) # Yeni regex ile
                title = title_element.get_text(strip=True) if title_element else "Başlık Yok"

                # İlan fiyatı
                # price_element = listing.find('div', class_='realty-price') # Eski
                price_element = listing.find('div', class_=re.compile(r'styles_price__')) # Yeni regex ile
                price_str = price_element.get_text(strip=True) if price_element else "Fiyat Yok"
                price = parse_price(price_str)

                # Konum bilgisi
                # location_element = listing.find('div', class_='realty-location') # Eski
                location_element = listing.find('div', class_=re.compile(r'styles_realtyLocation__')) # Yeni regex ile
                location_str = location_element.get_text(strip=True) if location_element else "Konum Yok"
                sehir, ilce, mahalle = parse_location(location_str)

                # Metrekare ve Oda Sayısı
                metrekare = None
                oda_sayisi = None
                
                # info_list = listing.find('div', class_='realty-info-list') # Eski
                # Emlakjet'in yeni yapısında bu bilgiler genellikle farklı span'lerin içinde oluyor
                # <span class="styles_propertyInfoListItem__..." ...>1+1</span>
                # <span class="styles_propertyInfoListItem__..." ...>90 m2</span>
                property_info_items = listing.find_all('span', class_=re.compile(r'styles_propertyInfoListItem__'))
                
                for item in property_info_items:
                    text = item.get_text(strip=True)
                    if 'm2' in text:
                        try:
                            metrekare = int(re.sub(r'[^\d]', '', text.replace('m2', '')))
                        except ValueError:
                            pass
                    elif '+' in text:
                        oda_sayisi = text
                
                # İlan URL'si
                item_url = "https://www.emlakjet.com" + listing['href'] if listing.has_attr('href') else None

                # İlan Tarihi (şimdilik veri çekme tarihini kullanacağız)
                ilan_tarihi = date.today()

                if not item_url:
                    print(f"Uyarı: {i+1}. ilan için URL bulunamadı, atlanıyor.")
                    continue
                if not price:
                    print(f"Uyarı: {i+1}. ilan için fiyat ayrıştırılamadı, atlanıyor. Fiyat stringi: {price_str}")
                    continue
                if not ilce:
                    print(f"Uyarı: {i+1}. ilan için ilçe ayrıştırılamadı, atlanıyor. Konum stringi: {location_str}")
                    continue

                # --- Veritabanına Kaydetme ---
                bolge, created_bolge = Bolge.objects.get_or_create(
                    sehir=sehir,
                    ilce=ilce,
                    mahalle=mahalle
                )
                if created_bolge:
                    print(f"Veritabanına yeni Bölge eklendi: {bolge}")

                kira_ilani_defaults = {
                    'bolge': bolge,
                    'fiyat': price,
                    'metrekare': metrekare,
                    'oda_sayisi': oda_sayisi,
                    'ilan_kaynagi': 'Emlakjet',
                    'ilan_tarihi': ilan_tarihi,
                }
                
                kira_ilani, created_ilan = KiraIlani.objects.update_or_create(
                    ilan_url=item_url,
                    defaults=kira_ilani_defaults
                )

                if created_ilan:
                    print(f"Veritabanına yeni Kira İlanı eklendi: {kira_ilani}")
                else:
                    print(f"Mevcut Kira İlanı güncellendi: {kira_ilani}")

            except Exception as e:
                print(f"İlan {i+1} işlenirken hata oluştu: {e}")
                import traceback
                print(traceback.format_exc())

except WebDriverException as e:
    print(f"WebDriver Hatası oluştu (ChromeDriver yolu veya uyumluluk sorunu): {e}")
    print("Lütfen ChromeDriver'ın doğru yerde ve Chrome tarayıcı sürümünüzle uyumlu olduğundan emin olun.")
except Exception as e:
    print(f"Beklenmeyen bir hata oluştu: {e}")
    if driver:
        with open("emlakjet_error_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Hata anındaki son sayfa içeriği 'emlakjet_error_page_source.html' dosyasına kaydedildi.")

finally:
    if driver:
        driver.quit()
        print("Chrome tarayıcısı kapatıldı.")