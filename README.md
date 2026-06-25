# Trạm sạc non-VinFast 🔌

Ứng dụng Flutter hiển thị các trạm sạc xe điện **không phải VinFast** trên bản đồ
Việt Nam: trạm sạc công cộng (cà phê, chung cư, cao tốc, các mạng EBOOST, EVPay,
EV ONE, EverCharge, SolarEV…) và các **showroom/đại lý** Audi, Ford, Geely, BYD có
trạm sạc công cộng.

> **1024 trạm** trong bản dữ liệu hiện tại — 1007 từ sacdien.net + 17 đại lý
> (Audi, Ford, BYD, Volvo, Wuling, Geely có trạm sạc **công cộng**).

## Kiến trúc (đơn giản, không server riêng)

```
sacdien.net (1063 trang /tram/)            đại lý (curated, 18 → geocode)
        │  scraper/scrape_sacdien.py              │  scraper/scrape_dealers.py
        │  (đọc JSON-LD trong mỗi trang)          │  (Nominatim/OSM geocode)
        ▼                                         ▼
        └──────────►  data/stations.json  ◄───────┘   (merge + dedup theo khoảng cách)
                            │
                 host trên GitHub (raw) ──────► app Flutter fetch lúc chạy
                            │                    (fallback: bản đóng gói trong app)
                            ▼
              GitHub Actions chạy lại mỗi ngày, commit dữ liệu mới
```

- **Không scrape lúc app chạy.** App chỉ tải 1 file JSON tĩnh (nhanh, nhẹ pin, không vỡ).
- **Nguồn dữ liệu chính:** [sacdien.net](https://sacdien.net) là WordPress; mỗi trang trạm
  có sẵn JSON-LD `schema.org/ElectricVehicleChargingStation` (tên, **toạ độ**, địa chỉ,
  SĐT, giờ, loại sạc, công suất kW, loại xe, thanh toán). Ổn định hơn nhiều so với parse HTML.
- **VinFast bị loại** ngay trong scraper (theo tên/slug/thương hiệu).

## Chạy app

```bash
cd app
flutter pub get
flutter run -d chrome      # hoặc -d <android/ios device>
flutter test               # kiểm thử logic model + bộ lọc
```

Tính năng: bản đồ cụm marker (OpenStreetMap), danh sách, tìm kiếm, lọc theo
**loại xe / nguồn / thương hiệu**, nút **"gần tôi"**, chi tiết trạm (chỉ đường, gọi điện).

## Cập nhật dữ liệu

```bash
# Scrape lại sacdien + gộp đại lý → data/stations.json
python scraper/scrape_sacdien.py --merge data/dealers.json --out data/stations.json
cp data/stations.json app/assets/stations.json   # cập nhật bản offline đóng gói

# Geocode lại danh sách đại lý (chỉ khi sửa scraper/dealers_seed.json)
python scraper/scrape_dealers.py

# Kiểm tra nhanh (không cần mạng)
python scraper/scrape_sacdien.py --self-check
python scraper/scrape_dealers.py --self-check
```

Scraper **chỉ dùng thư viện chuẩn Python** — không cần `pip install`.

## Triển khai data online (host + tự cập nhật)

Mục tiêu: data nằm online, **cập nhật ở đó là app tự nhận** — không cần build lại app.

1. Tạo 1 repo **public rỗng** trên github.com (không thêm README).
2. Chạy đúng 1 lệnh (nó tự nối app vào URL data + push):
   ```bash
   ./deploy.sh <github-user>/<repo>
   ```
3. Trên github.com → tab **Actions** → bật workflows. Từ đó
   [.github/workflows/scrape.yml](.github/workflows/scrape.yml) tự scrape lại **mỗi ngày**
   và commit `data/stations.json`.

**Cập nhật data sau này** — chọn 1 trong 3, app đều tự nhận (URL `kRemoteUrl` cố định):
- Sửa trực tiếp `data/stations.json` ngay trên giao diện web GitHub (thêm/xoá 1 trạm).
- Để Actions tự refresh hằng ngày.
- Chạy lại scraper ở máy rồi `git push`.

> App luôn có **bản đóng gói offline** trong assets làm fallback, nên chạy được ngay cả
> trước khi bạn deploy hay khi mất mạng.

## Giới hạn đã biết (ponytail ceilings)

- **OSM tiles trên Web bị CORS.** Bản đồ nền OpenStreetMap công cộng thường lỗi CORS
  trong trình duyệt. Cho production Web: đổi `urlTemplate` trong
  [app/lib/map_page.dart](app/lib/map_page.dart) sang nhà cung cấp có CORS + key
  (MapTiler/Stadia/Carto) hoặc tự host/cache tile. Marker/dữ liệu vẫn chạy bình thường.
- **Toạ độ đại lý là gần đúng** (`approx: true`) — geocode từ địa chỉ qua Nominatim;
  app đánh dấu rõ. 2/18 đại lý (địa chỉ KCN/phức hợp) chưa geocode được nên bị bỏ.
- **evchargingstops.com bị loại.** Site này chỉ nhúng iframe PlugShare và **không có
  dữ liệu trạm nào ở Việt Nam**.
- **"Trạm còn hoạt động?"** Không nguồn mở nào cho trạng thái **realtime** (cổng trống
  hay không) — chỉ app của nhà vận hành mới có. App hiện 2 tín hiệu tốt nhất có được:
  `last_updated` (ngày sacdien sửa listing) và — nếu bật OCM — `operational` (🟢/🔴 theo
  cộng đồng OpenChargeMap) + ngày xác minh.

## Khảo sát nguồn (kết luận trung thực, 2026-06)

- **sacdien.net là nguồn mở đầy đủ nhất** cho trạm non-VinFast ở VN. Hầu hết các mạng
  (Charge+, StarCharge, EverEV, DatCharge, Autel…) **chỉ có trong app, không có danh
  sách/API mở**. Ngoại lệ: **EBOOST** có layer Google My Maps công khai (mạng lớn nhất,
  ~220 điểm) — nhưng sacdien đã mirror ~244 điểm EBOOST nên net-new ít.
- **OpenChargeMap**: scraper [scrape_ocm.py](scraper/scrape_ocm.py) đã sẵn (cần key miễn
  phí, gắn qua secret `OCM_API_KEY`). **Cảnh báo: phủ VN mỏng & cũ** — gần như không
  operator VN nào đẩy dữ liệu lên OCM. Chỉ nên coi là nguồn bổ sung, lợi ích thấp.
- **Muốn phủ rộng hơn nữa** chỉ còn cách reverse-engineer API của các **app tổng hợp**
  (Trạm EV, EVCS.VN — Trạm EV còn quảng cáo tích hợp trạng thái cổng realtime). Đây là
  dự án riêng, phụ thuộc backend đóng + vướng ToS — cân nhắc kỹ.
```
