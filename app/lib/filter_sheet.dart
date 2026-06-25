import 'package:flutter/material.dart';
import 'store.dart';

/// Bottom sheet for source + brand filters (vehicle/search live in the app bar).
class FilterSheet extends StatefulWidget {
  const FilterSheet({super.key, required this.store});
  final StationStore store;

  static void show(BuildContext context, StationStore store) {
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => FilterSheet(store: store),
    );
  }

  @override
  State<FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<FilterSheet> {
  @override
  Widget build(BuildContext context) {
    final s = widget.store;
    final theme = Theme.of(context);
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.6,
      maxChildSize: 0.9,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        children: [
          Row(children: [
            Text('Bộ lọc', style: theme.textTheme.titleLarge),
            const Spacer(),
            if (s.hasFilters)
              TextButton(
                onPressed: () => setState(s.clearFilters),
                child: const Text('Xoá lọc'),
              ),
          ]),
          const SizedBox(height: 8),
          Text('Nguồn', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            for (final src in s.sources)
              FilterChip(
                label: Text(src),
                selected: s.selectedSources.contains(src),
                onSelected: (_) => setState(() => s.toggleSource(src)),
              ),
          ]),
          const SizedBox(height: 20),
          Text('Thương hiệu', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            for (final b in s.brands)
              FilterChip(
                label: Text(b),
                selected: s.selectedBrands.contains(b),
                onSelected: (_) => setState(() => s.toggleBrand(b)),
              ),
          ]),
        ],
      ),
    );
  }
}
