import 'package:flutter/material.dart';

void main() {
  runApp(const GemForgeApp());
}

class GemForgeApp extends StatelessWidget {
  const GemForgeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '__APP_NAME__',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tapCount = 0;

  void _increment() {
    setState(() {
      _tapCount += 1;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hello from GemForge')),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Core feature tap count:'),
            Text('$_tapCount', style: Theme.of(context).textTheme.headlineLarge),
            const SizedBox(height: 16),
            FilledButton(onPressed: _increment, child: const Text('Increment')),
          ],
        ),
      ),
    );
  }
}
