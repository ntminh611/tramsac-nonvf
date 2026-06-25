import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;
import 'package:http/http.dart' as http;
import 'station.dart';

/// Hosted, auto-refreshed dataset. Point this at your GitHub raw URL (or Pages)
/// once the repo is pushed, e.g.
///   https://raw.githubusercontent.com/USER/REPO/main/data/stations.json
/// Leave empty to use only the bundled snapshot.
const String kRemoteUrl = '';

/// Loads stations: try the hosted JSON first (fresh), fall back to the asset
/// bundled at build time (always works offline / before the URL is set).
///
/// ponytail: no on-disk cache layer — the bundled asset is the offline floor and
/// the remote is the fresh ceiling. Add shared_preferences/file caching only if a
/// "last fetched" cache between the two is ever actually needed.
Future<List<Station>> loadStations() async {
  if (kRemoteUrl.isNotEmpty) {
    try {
      final r = await http
          .get(Uri.parse(kRemoteUrl))
          .timeout(const Duration(seconds: 12));
      if (r.statusCode == 200) return _parse(utf8.decode(r.bodyBytes));
    } catch (_) {
      // network down / bad response -> fall through to the bundled snapshot
    }
  }
  return _parse(await rootBundle.loadString('assets/stations.json'));
}

List<Station> _parse(String body) {
  final doc = jsonDecode(body) as Map<String, dynamic>;
  final out = <Station>[];
  for (final s in (doc['stations'] as List? ?? const [])) {
    try {
      out.add(Station.fromJson(s as Map<String, dynamic>));
    } catch (_) {
      // skip any malformed record rather than failing the whole load
    }
  }
  return out;
}
