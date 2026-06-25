import 'dart:async';
import 'package:flutter/material.dart';
import 'data_source.dart';
import 'filter_sheet.dart';
import 'list_page.dart';
import 'map_page.dart';
import 'station.dart';
import 'store.dart';

void main() => runApp(const EvApp());

class EvApp extends StatelessWidget {
  const EvApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Trạm sạc non-VinFast',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.green,
        useMaterial3: true,
      ),
      home: const Loader(),
    );
  }
}

class Loader extends StatefulWidget {
  const Loader({super.key});
  @override
  State<Loader> createState() => _LoaderState();
}

class _LoaderState extends State<Loader> {
  late Future<List<Station>> _future = loadStations();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Station>>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        if (snap.hasError || (snap.data?.isEmpty ?? true)) {
          return Scaffold(
            body: Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Text('Không tải được dữ liệu trạm sạc.'),
                TextButton(
                  onPressed: () => setState(() => _future = loadStations()),
                  child: const Text('Thử lại'),
                ),
              ]),
            ),
          );
        }
        return Home(store: StationStore(snap.data!));
      },
    );
  }
}

class Home extends StatefulWidget {
  const Home({super.key, required this.store});
  final StationStore store;
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _tab = 0;
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearch(String q) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () => widget.store.setQuery(q));
  }

  @override
  Widget build(BuildContext context) {
    final store = widget.store;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 8,
        title: TextField(
          onChanged: _onSearch,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(
            hintText: 'Tìm theo tên, địa chỉ, tỉnh...',
            prefixIcon: Icon(Icons.search),
            border: InputBorder.none,
          ),
        ),
        actions: [
          ListenableBuilder(
            listenable: store,
            builder: (context, _) => IconButton(
              tooltip: 'Bộ lọc',
              onPressed: () => FilterSheet.show(context, store),
              icon: Badge(
                isLabelVisible:
                    store.selectedBrands.isNotEmpty || store.selectedSources.isNotEmpty,
                child: const Icon(Icons.tune),
              ),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: ListenableBuilder(
            listenable: store,
            builder: (context, _) => SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(children: [
                for (final v in VehicleFilter.values)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(switch (v) {
                        VehicleFilter.all => 'Tất cả',
                        VehicleFilter.car => 'Ô tô điện',
                        VehicleFilter.moto => 'Xe máy điện',
                      }),
                      selected: store.vehicle == v,
                      onSelected: (_) => store.setVehicle(v),
                    ),
                  ),
              ]),
            ),
          ),
        ),
      ),
      body: ListenableBuilder(
        listenable: store,
        builder: (context, _) => IndexedStack(
          index: _tab,
          children: [
            MapPage(store: store),
            ListPage(store: store),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.map_outlined), selectedIcon: Icon(Icons.map), label: 'Bản đồ'),
          NavigationDestination(
              icon: Icon(Icons.list), selectedIcon: Icon(Icons.list_alt), label: 'Danh sách'),
        ],
      ),
    );
  }
}
