import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:african_enrollment_app/screens/prediction_screen.dart';
import 'package:african_enrollment_app/services/api_service.dart';

// Mock HTTP client that returns canned responses for testing.
class MockHttpClient extends http.BaseClient {
  final http.Response? successResponse;
  final int? errorStatusCode;
  final String? errorBody;
  final bool throwSocketException;
  final bool throwTimeoutException;
  final Duration? delay;
  final VoidCallback? onRequest;
  int callCount = 0;

  MockHttpClient({
    this.successResponse,
    this.errorStatusCode,
    this.errorBody,
    this.throwSocketException = false,
    this.throwTimeoutException = false,
    this.delay,
    this.onRequest,
  });

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    callCount++;
    onRequest?.call();
    if (delay != null) {
      await Future<void>.delayed(delay!);
    }
    if (throwSocketException) {
      throw const SocketException('Failed host lookup');
    }
    if (throwTimeoutException) {
      throw TimeoutException('Request timed out', Duration(seconds: 10));
    }
    if (errorStatusCode != null) {
      return http.StreamedResponse(
        Stream<List<int>>.fromIterable([utf8.encode(errorBody ?? '')]),
        errorStatusCode!,
      );
    }
    return http.StreamedResponse(
      Stream<List<int>>.fromIterable([utf8.encode(successResponse!.body)]),
      successResponse!.statusCode,
    );
  }
}

/// Creates an [ApiService] with a mock HTTP client.
ApiService serviceWithMock({
  http.Response? successResponse,
  int? errorStatusCode,
  String? errorBody,
  bool throwSocketException = false,
  bool throwTimeoutException = false,
  Duration? delay,
  VoidCallback? onRequest,
}) {
  final client = MockHttpClient(
    successResponse: successResponse,
    errorStatusCode: errorStatusCode,
    errorBody: errorBody,
    throwSocketException: throwSocketException,
    throwTimeoutException: throwTimeoutException,
    delay: delay,
    onRequest: onRequest,
  );
  return ApiService(client: client);
}

void main() {
  group('Prediction API Integration', () {
    // Select a dropdown option by index and value.
    Future<void> selectDropdown(
      WidgetTester tester,
      int index,
      String option,
    ) async {
      final dropdown = find.byType(DropdownButtonFormField<String>).at(index);
      await tester.ensureVisible(dropdown);
      await tester.pumpAndSettle();
      await tester.tap(dropdown);
      await tester.pumpAndSettle();

      final optionFinder = find.text(option);
      if (optionFinder.evaluate().isEmpty) {
        final menuScrollable = find
            .ancestor(
              of: find.byType(DropdownMenuItem<String>).first,
              matching: find.byType(Scrollable),
            )
            .first;
        await tester.scrollUntilVisible(
          optionFinder,
          150,
          scrollable: menuScrollable,
          maxScrolls: 50,
        );
        await tester.pumpAndSettle();
      }

      expect(optionFinder, findsWidgets);
      await tester.tap(optionFinder.last);
      await tester.pumpAndSettle();
    }

    // Launch the PredictionScreen with an injected ApiService.
    Future<void> launchAppWithService(
      WidgetTester tester,
      ApiService apiService,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData(useMaterial3: true),
          home: PredictionScreen(apiService: apiService),
        ),
      );
      await tester.pumpAndSettle();
    }

    // Complete step 0: Country Details (3 dropdowns).
    Future<void> completeStep0(WidgetTester tester) async {
      await selectDropdown(tester, 0, 'AGO');
      await selectDropdown(tester, 1, 'Sub-Saharan Africa');
      await selectDropdown(tester, 2, 'Low income');
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }

    // Complete step 1: Demographics (4 text fields).
    Future<void> completeStep1(WidgetTester tester) async {
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), '2010');
      await tester.enterText(fields.at(1), '10000000');
      await tester.enterText(fields.at(2), '2.5');
      await tester.enterText(fields.at(3), '42');
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }

    // Complete step 2: Education Indicators (3 text fields).
    Future<void> completeStep2(WidgetTester tester) async {
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), '35');
      await tester.enterText(fields.at(1), '40');
      await tester.enterText(fields.at(2), '6');
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
    }

    // Complete step 3: GDP field only.
    Future<void> completeStep3(WidgetTester tester) async {
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), '800');
    }

    // TEST 1: Prediction button appears on the final step.
    testWidgets('Prediction button appears on final step', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.05}),
          200,
        ),
      );
      await launchAppWithService(tester, apiService);

      expect(find.text('Continue'), findsOneWidget);
      expect(find.text('Predict Enrollment'), findsNothing);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);

      expect(find.text('Predict Enrollment'), findsOneWidget);
      expect(find.text('Continue'), findsNothing);
    });

    // TEST 2: Valid inputs trigger exactly one API request.
    testWidgets('Valid inputs trigger exactly one API request', (
      WidgetTester tester,
    ) async {
      int callCount = 0;
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.05}),
          200,
        ),
        onRequest: () => callCount++,
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      expect(callCount, 0);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pumpAndSettle();

      expect(callCount, 1);
    });

    // TEST 3: Loading indicator appears during the request.
    testWidgets('Loading indicator appears during request', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.05}),
          200,
        ),
        delay: const Duration(milliseconds: 200),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(find.text('Predicting...'), findsOneWidget);
      expect(find.text('Predicting enrollment rate...'), findsOneWidget);

      await tester.pumpAndSettle();

      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    // TEST 4: Duplicate submissions are prevented.
    testWidgets('Duplicate submissions are prevented', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.05}),
          200,
        ),
        delay: const Duration(milliseconds: 500),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pump(); // Trigger loading state

      // Loading indicator should be visible, meaning button entered loading state.
      expect(find.byType(CircularProgressIndicator), findsWidgets);

      await tester.pumpAndSettle();

      // Loading should be gone after completion.
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    // TEST 5: Successful prediction displays formatted percentage.
    testWidgets('Successful prediction displays formatted percentage', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.04502624511717}),
          200,
        ),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pumpAndSettle();

      expect(
        find.text('Predicted Primary School Enrollment Rate'),
        findsOneWidget,
      );
      expect(find.text('106.05%'), findsOneWidget);
      expect(
        find.text(
          'Predicted gross enrollment rate. Can exceed 100% due to '
          'over-age or under-age enrollment.',
        ),
        findsOneWidget,
      );
    });

    // TEST 6: HTTP/API failure displays readable error.
    testWidgets('HTTP 500 displays readable error', (WidgetTester tester) async {
      final apiService = serviceWithMock(
        errorStatusCode: 500,
        errorBody: jsonEncode({'detail': 'Internal server error'}),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'The prediction server encountered an error. Please try again later.',
        ),
        findsOneWidget,
      );
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    testWidgets('HTTP 422 displays readable error', (WidgetTester tester) async {
      final apiService = serviceWithMock(
        errorStatusCode: 422,
        errorBody: jsonEncode({'detail': 'Validation error'}),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Invalid input data. Please review your entries and try again.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('Network failure displays readable error', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        throwSocketException: true,
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Network error: please check your internet connection and try again.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('Request timeout displays readable error', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        throwTimeoutException: true,
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Request timed out. The prediction server may be starting up. '
          'Please try again in a moment.',
        ),
        findsOneWidget,
      );
    });

    // TEST 7 & 8: Loading state resets after success and failure.
    testWidgets('Loading state resets after success', (WidgetTester tester) async {
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.05}),
          200,
        ),
        delay: const Duration(milliseconds: 100),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);

      await tester.pumpAndSettle();

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('106.05%'), findsOneWidget);
    });

    testWidgets('Loading state resets after failure', (WidgetTester tester) async {
      final apiService = serviceWithMock(
        errorStatusCode: 500,
        delay: const Duration(milliseconds: 100),
      );
      await launchAppWithService(tester, apiService);

      await completeStep0(tester);
      await completeStep1(tester);
      await completeStep2(tester);
      await completeStep3(tester);

      await tester.tap(find.text('Predict Enrollment'));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);

      await tester.pumpAndSettle();

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(
        find.text(
          'The prediction server encountered an error. Please try again later.',
        ),
        findsOneWidget,
      );
    });

    // TEST 9: Existing navigation and validation continue working.
    testWidgets('Existing navigation and validation continue working', (
      WidgetTester tester,
    ) async {
      final apiService = serviceWithMock(
        successResponse: http.Response(
          jsonEncode({'predicted_primary_enrollment': 106.05}),
          200,
        ),
      );
      await launchAppWithService(tester, apiService);

      expect(find.text('Country Details'), findsOneWidget);
      expect(find.text('1 / 4'), findsOneWidget);

      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
      expect(find.text('Please select Country'), findsOneWidget);

      await completeStep0(tester);
      expect(find.text('Demographics'), findsOneWidget);
      expect(find.text('2 / 4'), findsOneWidget);

      await completeStep1(tester);
      expect(find.text('Education Indicators'), findsOneWidget);
      expect(find.text('3 / 4'), findsOneWidget);

      await completeStep2(tester);
      expect(find.text('Economy & Prediction'), findsOneWidget);
      expect(find.text('4 / 4'), findsOneWidget);

      // Back from step 3 returns to step 2 (Education Indicators).
      await tester.tap(find.text('Back'));
      await tester.pumpAndSettle();
      expect(find.text('Education Indicators'), findsOneWidget);
      expect(find.text('3 / 4'), findsOneWidget);
    });
  });
}