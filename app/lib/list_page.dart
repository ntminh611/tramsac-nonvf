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
        return ListTile(
          leading: Icon(s.isDealer ? Icons.store : Icons.ev_station,
              color: s.isDealer ? Colors.orange.shade800 : Colors.green.shade700),
          title: Text(s.name, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(
            [s.province, s.brand, s.powerKw].where((e) => e != null && e.isNotEmpty).join(' • '),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: dist == null
              ? null
              : Text('${dist.toStringAsFixed(dist < 10 ? 1 : 0)} km',
                  style: Theme.of(context).textTheme.labelSmall),
          onTap: () => StationSheet.show(context, s, distanceKm: dist),
        );
      },
    );
  }
}
