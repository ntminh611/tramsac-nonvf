import 'package:flutter/material.dart';
import 'station_sheet.dart';
import 'store.dart';

class ListPage extends StatelessWidget {
  const ListPage({super.key, required this.store});
  final StationStore store;

  @override
  Widget build(BuildContext context) {
    final stations = store.filtered;
    if (stations.isEmpty) {
      return const Center(child: Text('Không có trạm nào khớp bộ lọc.'));
    }
    return ListView.separated(
      itemCount: stations.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, i) {
        final s = stations[i];
        final dist = store.distanceKm(s);
        final theme = Theme.of(context);
        // meta = brand • power • price (province dropped — the address already names the city)
        final meta = [s.brand, s.powerKw, s.price].where((e) => e != null && e.isNotEmpty).join(' • ');
        final lines = <Widget>[
          if (s.address != null)
            Text(s.address!, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyMedium),
          if (meta.isNotEmpty)
            Text(meta, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.outline)),
        ];
        return ListTile(
          leading: Icon(s.isDealer ? Icons.store : Icons.ev_station,
              color: s.isDealer ? Colors.orange.shade800 : Colors.green.shade700),
          title: Text(s.name, maxLines: 1, overflow: TextOverflow.ellipsis),
          isThreeLine: lines.length > 1,
          subtitle: lines.isEmpty
              ? null
              : Column(crossAxisAlignment: CrossAxisAlignment.start, children: lines),
          trailing: dist == null
              ? null
              : Text('${dist.toStringAsFixed(dist < 10 ? 1 : 0)} km',
                  style: theme.textTheme.labelSmall),
          onTap: () => StationSheet.show(context, s, distanceKm: dist),
        );
      },
    );
  }
}
