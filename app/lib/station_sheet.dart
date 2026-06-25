import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'station.dart';

/// Bottom sheet shown when a station marker / list row is tapped.
class StationSheet extends StatelessWidget {
  const StationSheet({super.key, required this.station, this.distanceKm});

  final Station station;
  final double? distanceKm;

  static void show(BuildContext context, Station s, {double? distanceKm}) {
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => StationSheet(station: s, distanceKm: distanceKm),
    );
  }

  Future<void> _open(Uri uri) async {
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = station;
    final theme = Theme.of(context);
    final chips = <Widget>[
      if (s.brand != null) _chip(theme, Icons.business, s.brand!),
      if (s.powerKw != null) _chip(theme, Icons.bolt, s.powerKw!),
      if (s.connector != null) _chip(theme, Icons.power, s.connector!),
      for (final v in s.vehicleTypes) _chip(theme, Icons.directions_car, v),
      _chip(theme, Icons.travel_explore, s.source),
    ];

    return Padding(
      padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(s.name, style: theme.textTheme.titleLarge),
          const SizedBox(height: 4),
          if (s.address != null)
            Text(s.address!, style: theme.textTheme.bodyMedium),
          if (s.approx)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Vị trí gần đúng (geocode từ địa chỉ)',
                  style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.error)),
            ),
          if (distanceKm != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Cách bạn ${distanceKm!.toStringAsFixed(1)} km',
                  style: theme.textTheme.bodySmall),
            ),
          if (s.operational == false)
            _statusBanner(theme, theme.colorScheme.error, Icons.warning_amber,
                'Có thể đã ngừng hoạt động (theo OpenChargeMap)'),
          if (s.operational == true)
            _statusBanner(theme, Colors.green.shade700, Icons.check_circle,
                'Đang hoạt động (theo OpenChargeMap)'),
          if (s.price != null)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Row(children: [
                Icon(Icons.sell, size: 20, color: theme.colorScheme.primary),
                const SizedBox(width: 6),
                Text('Giá: ${s.price}',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(color: theme.colorScheme.primary, fontWeight: FontWeight.w600)),
              ]),
            ),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: chips),
          if (s.hours != null || s.payment != null) const SizedBox(height: 12),
          if (s.hours != null) _line(theme, Icons.access_time, s.hours!),
          if (s.payment != null) _line(theme, Icons.payment, s.payment!),
          if (s.lastUpdated != null)
            _line(theme, Icons.update, 'Cập nhật: ${s.lastUpdated}'),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: () => _open(Uri.parse(
                    'https://www.google.com/maps/dir/?api=1&destination=${s.pos.latitude},${s.pos.longitude}')),
                icon: const Icon(Icons.directions),
                label: const Text('Chỉ đường'),
              ),
            ),
            if (s.phone != null) ...[
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: () => _open(Uri(scheme: 'tel', path: s.phone!.replaceAll(' ', ''))),
                icon: const Icon(Icons.call),
                label: const Text('Gọi'),
              ),
            ],
          ]),
          if (s.url != null)
            TextButton.icon(
              onPressed: () => _open(Uri.parse(s.url!)),
              icon: const Icon(Icons.open_in_new, size: 18),
              label: const Text('Xem nguồn'),
            ),
        ],
      ),
    );
  }

  Widget _statusBanner(ThemeData t, Color color, IconData icon, String text) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Row(children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 6),
          Expanded(child: Text(text, style: t.textTheme.bodyMedium?.copyWith(color: color))),
        ]),
      );

  Widget _chip(ThemeData t, IconData i, String label) => Chip(
        avatar: Icon(i, size: 16),
        label: Text(label),
        visualDensity: VisualDensity.compact,
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      );

  Widget _line(ThemeData t, IconData i, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(i, size: 18, color: t.colorScheme.outline),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: t.textTheme.bodyMedium)),
        ]),
      );
}
