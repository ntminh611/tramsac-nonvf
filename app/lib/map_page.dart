import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_marker_cluster/flutter_map_marker_cluster.dart';
import 'package:latlong2/latlong.dart';
import 'station.dart';
import 'station_sheet.dart';
import 'store.dart';

/// OSM tiles. userAgentPackageName MUST be a real unique id — OSM blocks generic
/// ones. ponytail ceiling: the public OSM tile server is rate-limited and fails
/// CORS on Web (browser sets its own UA). Upgrade path for production/Web: swap
/// urlTemplate to a CORS-friendly provider with a key (MapTiler/Stadia/Carto) or
/// self-host + cache tiles (e.g. flutter_map_tile_caching). Markers/data are fine.
const _tileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const _userAgent = 'net.sacdienmap.app';
const _vietnam = LatLng(16.0, 107.8);

class MapPage extends StatefulWidget {
  const MapPage({super.key, required this.store});
  final StationStore store;

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  final _controller = MapController();

  Marker _marker(Station s) {
    final color = s.isDealer ? Colors.orange.shade800 : Colors.green.shade700;
    return Marker(
      point: s.pos,
      width: 36,
      height: 36,
      child: GestureDetector(
        onTap: () => StationSheet.show(context, s, distanceKm: widget.store.distanceKm(s)),
        child: Icon(s.approx ? Icons.ev_station_outlined : Icons.ev_station,
            color: color, size: 32),
      ),
    );
  }

  Future<void> _goToMe() async {
    final messenger = ScaffoldMessenger.of(context);
    final pos = await widget.store.locate();
    if (pos == null) {
      messenger.showSnackBar(const SnackBar(
          content: Text('Không lấy được vị trí. Hãy bật định vị & cấp quyền.')));
      return;
    }
    _controller.move(pos, 13);
  }

  @override
  Widget build(BuildContext context) {
    final stations = widget.store.filtered;
    return Stack(children: [
      FlutterMap(
        mapController: _controller,
        options: const MapOptions(
          initialCenter: _vietnam,
          initialZoom: 5.4,
          minZoom: 4,
          maxZoom: 18,
        ),
        children: [
          TileLayer(urlTemplate: _tileUrl, userAgentPackageName: _userAgent, maxZoom: 19),
          MarkerClusterLayerWidget(
            options: MarkerClusterLayerOptions(
              maxClusterRadius: 50,
              size: const Size(44, 44),
              markers: [for (final s in stations) _marker(s)],
              padding: const EdgeInsets.all(50),
              builder: (context, markers) => DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Theme.of(context).colorScheme.primary,
                ),
                child: Center(
                  child: Text('${markers.length}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ),
            ),
          ),
        ],
      ),
      Positioned(
        left: 8,
        bottom: 8,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          color: Colors.white70,
          child: const Text('© OpenStreetMap', style: TextStyle(fontSize: 10)),
        ),
      ),
      Positioned(
        right: 12,
        top: 12,
        child: Material(
          elevation: 2,
          borderRadius: BorderRadius.circular(20),
          color: Theme.of(context).colorScheme.surface,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Text('${stations.length} trạm'),
          ),
        ),
      ),
      Positioned(
        right: 12,
        bottom: 16,
        child: FloatingActionButton(
          heroTag: 'locate',
          onPressed: _goToMe,
          child: const Icon(Icons.my_location),
        ),
      ),
    ]);
  }
}
