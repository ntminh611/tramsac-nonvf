// Logic checks for the station model + filtering store.
import 'package:flutter_test/flutter_test.dart';
import 'package:sacdien_map/station.dart';
import 'package:sacdien_map/store.dart';

const _carJson = {
  'id': 'sacdien:audi-hanoi',
  'source': 'sacdien.net',
  'name': 'Trạm sạc EV ONE - Audi Hà Nội',
  'brand': 'EV One',
  'lat': '21.0123',
  'lng': '105.7841',
  'address': '8 Phạm Hùng, TP. Hà Nội',
  'province': 'TP. Hà Nội',
  'power_kw': '180kW',
  'connector': 'CCS2',
  'vehicle_types': ['Xe hơi điện'],
  'last_updated': '2026-04-17',
  'operational': true,
};

const _motoJson = {
  'id': 'sacdien:cafe-hcm',
  'source': 'sacdien.net',
  'name': 'Quán cà phê Quận 1',
  'lat': 10.78,
  'lng': 106.7,
  'province': 'TP. Hồ Chí Minh',
  'vehicle_types': ['Xe máy điện'],
};

void main() {
  test('Station.fromJson parses string + numeric coords and vehicle flags', () {
    final car = Station.fromJson(Map<String, dynamic>.from(_carJson));
    expect(car.pos.latitude, 21.0123);
    expect(car.isCar, isTrue);
    expect(car.isMotorbike, isFalse);
    expect(car.brand, 'EV One');
    expect(car.lastUpdated, '2026-04-17');
    expect(car.operational, isTrue);

    final moto = Station.fromJson(Map<String, dynamic>.from(_motoJson));
    expect(moto.isMotorbike, isTrue);
    expect(moto.isCar, isFalse);
    expect(moto.brand, isNull);
  });

  test('Station.fromJson rejects records without coordinates', () {
    expect(() => Station.fromJson({'id': 'x', 'name': 'no-geo'}), throwsFormatException);
  });

  test('StationStore filters by vehicle, brand and free-text query', () {
    final store = StationStore([
      Station.fromJson(Map<String, dynamic>.from(_carJson)),
      Station.fromJson(Map<String, dynamic>.from(_motoJson)),
    ]);
    expect(store.filtered.length, 2);
    expect(store.brands, ['EV One']);

    store.setVehicle(VehicleFilter.moto);
    expect(store.filtered.single.name, contains('cà phê'));

    store.setVehicle(VehicleFilter.all);
    store.toggleBrand('EV One');
    expect(store.filtered.single.brand, 'EV One');

    store.clearFilters();
    store.setQuery('hà nội');
    expect(store.filtered.single.province, 'TP. Hà Nội');
  });
}
