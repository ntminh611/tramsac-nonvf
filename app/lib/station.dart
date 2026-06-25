import 'package:latlong2/latlong.dart';

/// One charging station, matching the JSON produced by the scraper.
class Station {
  final String id;
  final String source; // "sacdien.net" or "Đại lý <Brand>"
  final String name;
  final String? brand;
  final LatLng pos;
  final String? address;
  final String? province;
  final String? phone;
  final String? hours;
  final String? powerKw;
  final String? connector;
  final List<String> vehicleTypes;
  final String? payment;
  final String? url;
  final bool approx; // geocoded (dealer) -> position is approximate
  final String? lastUpdated; // YYYY-MM-DD the listing was last edited/verified
  final bool? operational; // OCM status: true/false/null(unknown)

  const Station({
    required this.id,
    required this.source,
    required this.name,
    required this.pos,
    this.brand,
    this.address,
    this.province,
    this.phone,
    this.hours,
    this.powerKw,
    this.connector,
    this.vehicleTypes = const [],
    this.payment,
    this.url,
    this.approx = false,
    this.lastUpdated,
    this.operational,
  });

  bool get isDealer => source.toLowerCase().contains('đại lý') || source.startsWith('dealer');
  bool get isCar => vehicleTypes.any((v) => v.contains('hơi') || v.contains('ô tô') || v.contains('Ô tô'));
  bool get isMotorbike => vehicleTypes.any((v) => v.contains('máy'));

  static double? _d(Object? v) => v == null ? null : double.tryParse(v.toString());

  factory Station.fromJson(Map<String, dynamic> j) {
    final lat = _d(j['lat']), lng = _d(j['lng']);
    if (lat == null || lng == null) {
      throw const FormatException('station missing coordinates');
    }
    return Station(
      id: j['id']?.toString() ?? '${lat}_$lng',
      source: j['source']?.toString() ?? 'sacdien.net',
      name: j['name']?.toString() ?? 'Trạm sạc',
      brand: j['brand']?.toString(),
      pos: LatLng(lat, lng),
      address: j['address']?.toString(),
      province: j['province']?.toString(),
      phone: j['phone']?.toString(),
      hours: j['hours']?.toString(),
      powerKw: j['power_kw']?.toString(),
      connector: j['connector']?.toString(),
      vehicleTypes: (j['vehicle_types'] as List?)?.map((e) => e.toString()).toList() ?? const [],
      payment: j['payment']?.toString(),
      url: j['url']?.toString(),
      approx: j['approx'] == true,
      lastUpdated: j['last_updated']?.toString(),
      operational: j['operational'] is bool ? j['operational'] as bool : null,
    );
  }
}
