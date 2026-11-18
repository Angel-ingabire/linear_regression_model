import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:flutter_test/flutter_test.dart';

import 'package:african_enrollment_app/services/api_service.dart';

void main() {
  group('ApiService', () {
    final validInputs = {
      'year': 2010,
      'population': 10000000.0,
      'population_growth': 2.5,
      'population_age_0_14': 42.0,
      'secondary_enrollment': 35.0,
      'pupil_teacher_ratio': 40.0,
      'primary_education_duration': 6,
      'gdp_per_capita': 800.0,
      'country_code': 'RWA',
      'region': 'Sub-Saharan Africa',
      'income_group': 'Low income',
    };

    MockClient createClient({
      required int statusCode,
      required String body,
      Duration? delay,
      bool throwSocketException = false,
      bool throwTimeoutException = false,
      bool throwClientException = false,
    }) {
      return MockClient(
        statusCode: statusCode,
        body: body,
        delay: delay,
        throwSocketException: throwSocketException,
        throwTimeoutException: throwTimeoutException,
        throwClientException: throwClientException,
      );
    }

    test('returns predicted_primary_enrollment for HTTP 200 with double', () async {
      final client = createClient(
        statusCode: 200,
        body: jsonEncode({'predicted_primary_enrollment': 106.04502624511717}),
      );
      final service = ApiService(client: client);

      final result = await service.predictEnrollment(validInputs);

      expect(result, 106.04502624511717);
    });

    test('returns predicted_primary_enrollment for HTTP 200 with integer', () async {
      final client = createClient(
        statusCode: 200,
        body: jsonEncode({'predicted_primary_enrollment': 106}),
      );
      final service = ApiService(client: client);

      final result = await service.predictEnrollment(validInputs);

      expect(result, 106.0);
    });

    test('throws ApiException for HTTP 422', () async {
      final client = createClient(
        statusCode: 422,
        body: jsonEncode({'detail': 'Validation error'}),
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'Invalid input data. Please review your entries and try again.',
        )),
      );
    });

    test('throws ApiException for HTTP 500', () async {
      final client = createClient(
        statusCode: 500,
        body: jsonEncode({'detail': 'Internal server error'}),
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'The prediction server encountered an error. Please try again later.',
        )),
      );
    });

    test('throws ApiException for request timeout', () async {
      final client = createClient(
        statusCode: 200,
        body: '',
        throwTimeoutException: true,
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'Request timed out. The prediction server may be starting up. '
          'Please try again in a moment.',
        )),
      );
    });

    test('throws ApiException for invalid JSON response', () async {
      final client = createClient(
        statusCode: 200,
        body: 'not json',
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'Invalid response format from the prediction server.',
        )),
      );
    });

    test('throws ApiException when predicted_primary_enrollment is missing', () async {
      final client = createClient(
        statusCode: 200,
        body: jsonEncode({'other_field': 123}),
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'The server response is missing the prediction result.',
        )),
      );
    });

    test('throws ApiException when predicted_primary_enrollment is null', () async {
      final client = createClient(
        statusCode: 200,
        body: jsonEncode({'predicted_primary_enrollment': null}),
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'The prediction result is invalid.',
        )),
      );
    });

    test('throws ApiException when predicted_primary_enrollment is a string', () async {
      final client = createClient(
        statusCode: 200,
        body: jsonEncode({'predicted_primary_enrollment': 'not a number'}),
      );
      final service = ApiService(client: client);

      expect(
        () => service.predictEnrollment(validInputs),
        throwsA(isA<ApiException>().having(
          (e) => e.message,
          'message',
          'The prediction result is not a valid number.',
        )),
      );
    });

    test('sends correct JSON request body with all 11 inputs', () async {
      late Map<String, dynamic>? capturedBody;
      late String? capturedContentType;

      final client = MockClient(
        statusCode: 200,
        body: jsonEncode({'predicted_primary_enrollment': 50.0}),
        onRequest: (request) {
          final req = request as http.Request;
          capturedBody = jsonDecode(req.body);
          capturedContentType = req.headers['content-type'];
        },
      );
      final service = ApiService(client: client);

      await service.predictEnrollment(validInputs);

      expect(capturedBody, validInputs);
      expect(capturedContentType, contains('application/json'));
    });

    test('uses configurable http.Client for injection', () {
      final client = MockClient(
        statusCode: 200,
        body: jsonEncode({'predicted_primary_enrollment': 1.0}),
      );
      final service = ApiService(client: client);

      expect(service, isA<ApiService>());
    });
  });
}

/// Minimal mock http.Client for testing ApiService without network calls.
class MockClient extends http.BaseClient {
  final int statusCode;
  final String body;
  final Duration? delay;
  final bool throwSocketException;
  final bool throwTimeoutException;
  final bool throwClientException;
  final void Function(http.BaseRequest request)? onRequest;

  MockClient({
    required this.statusCode,
    required this.body,
    this.delay,
    this.throwSocketException = false,
    this.throwTimeoutException = false,
    this.throwClientException = false,
    this.onRequest,
  });

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (throwClientException) {
      throw http.ClientException('Client error');
    }

    if (onRequest != null) {
      onRequest!(request);
    }

    if (throwSocketException) {
      throw const SocketException('Failed host lookup');
    }

    if (throwTimeoutException) {
      throw TimeoutException('Request timed out', Duration(seconds: 10));
    }

    if (delay != null) {
      await Future<void>.delayed(delay!);
    }

    final stream = Stream<List<int>>.fromIterable([utf8.encode(body)]);
    return http.StreamedResponse(stream, statusCode);
  }
}