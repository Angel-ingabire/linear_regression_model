import 'package:flutter/material.dart';
import 'screens/prediction_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const EnrollmentApp());
}

class EnrollmentApp extends StatelessWidget {
  const EnrollmentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'African Primary School Enrollment Predictor',
      debugShowCheckedModeBanner: false,

      // Application theme
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo,
          brightness: Brightness.light,
        ),

        // App bar appearance
        appBarTheme: const AppBarTheme(centerTitle: true, elevation: 0),

        // Input field appearance
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
        ),

        // Button appearance
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ),

      // Starting screen
      home: const PredictionScreen(),
    );
  }
}
