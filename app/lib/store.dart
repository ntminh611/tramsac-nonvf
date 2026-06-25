import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'station.dart';

enum VehicleFilter { all, car, moto }

/// Shared state for the map + list tabs. Plain ChangeNotifier so we need no
/// state-management dependency — Flutter's ListenableBuilder consumes it.
class StationStore extends ChangeNotifier {
  StationStore(this.all) {
    brands = {for (final s in all) if (s.brand != null) s.brand!}.toList()..sort();
    sources = {for (final s in all) s.source}.toList()..sort();
  }

  final List<Station> all;
  late final List<String> brands;
  late final List<String> sources;

  static const _distance = Distance();

  // --- filter state ---
  String query = '';
  VehicleFilter vehicle = VehicleFilter.all;
  final Set<String> selectedBrands = {}; // empty = all brands
  final Set<String> selectedSources = {}; // empty = all sources
  LatLng? userLocation;

  bool get hasFilters =>
      query.isNotEmpty ||
      vehicle != VehicleFilter.all ||
      selectedBrands.isNotEmpty ||
      selectedSources.isNotEmpty;

  void setQuery(String q) {
    query = q.trim();
    notifyListeners();
  }

  void setVehicle(VehicleFilter v) {
    vehicle = v;
    notifyListeners();
  }

  void toggleBrand(String b) {
    selectedBrands.contains(b) ? selectedBrands.remove(b) : selectedBrands.add(b);
    notifyListeners();
  }

  void toggleSource(String s) {
    selectedSources.contains(s) ? selectedSources.remove(s) : selectedSources.add(s);
    notifyListeners();
  }

  void clearFilters() {
    query = '';
    vehicle = VehicleFilter.all;
    selectedBrands.clear();
    selectedSources.clear();
    notifyListeners();
  }

  bool _matches(Station s) {
    if (selectedSources.isNotEmpty && !selectedSources.contains(s.source)) return false;
    if (selectedBrands.isNotEmpty && (s.brand == null || !selectedBrands.contains(s.brand))) {
      return false;
    }
    if (vehicle == VehicleFilter.car && !s.isCar) return false;
    if (vehicle == VehicleFilter.moto && !s.isMotorbike) return false;
    if (query.isNotEmpty) {
      final hay = '${s.name} ${s.address ?? ''} ${s.province ?? ''} ${s.brand ?? ''}'.toLowerCase();
      if (!hay.contains(query.toLowerCase())) return false;
    }
    return true;
  }

  double? distanceKm(Station s) => userLocation == null
      ? null
      : _distance.as(LengthUnit.Kilometer, userLocation!, s.pos);

  /// Filtered stations, sorted by distance when we know where the user is.
  List<Station> get filtered {
    final out = all.where(_matches).toList();
    if (userLocation != null) {
      out.sort((a, b) => _distance
          .as(LengthUnit.Meter, userLocation!, a.pos)
          .compareTo(_distance.as(LengthUnit.Meter, userLocation!, b.pos)));
    } else {
      out.sort((a, b) => a.name.compareTo(b.name));
    }
    return out;
  }

  /// Ask the OS for the current position; returns it (and stores it) or null.
  Future<LatLng?> locate() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        return null;
      }
      final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.medium),
      );
      userLocation = LatLng(p.latitude, p.longitude);
      notifyListeners();
      return userLocation;
    } catch (_) {
      return null;
    }
  }
}
