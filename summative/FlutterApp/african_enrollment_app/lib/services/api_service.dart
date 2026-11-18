import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

/// Base URL for the EnrollmentIQ prediction API hosted on Render.
const String _baseUrl = 'https://african-enrollment-api.onrender.com';

/// Prediction endpoint path.
const String _predictEndpoint = '/predict';

/// Timeout for API requests, allowing for Render cold starts.
const Duration _requestTimeout = Duration(seconds: 90);

/// Thrown when the API service encounters an error that should be
/// surfaced to the user with a clear, non-sensitive message.
class ApiException implements Exception {
  final String message;

  const ApiException(this.message);

  @override
  String toString() => message;
}

/// Service for communicating with the EnrollmentIQ prediction API.
///
/// The [http.Client] is injected so the service can be unit-tested with
/// mocked responses instead of hitting the live Render server.
class ApiService {
  final http.Client _client;

  /// Creates an [ApiService] with an optional custom [http.Client].
  ///
  /// When [client] is omitted, a real [http.Client] is used.
  ApiService({http.Client? client}) : _client = client ?? http.Client();

  /// Sends the 11 machine-learning inputs to the prediction API and
  /// returns the predicted primary enrollment value.
  ///
  /// Throws [ApiException] with a user-friendly message for:
  ///   - HTTP 422 validation failures
  ///   - HTTP 500 server errors
  ///   - Network / connection failures
  ///   - Request timeouts
  ///   - Malformed JSON responses
  ///   - Missing or invalid `predicted_primary_enrollment` values
  Future<double> predictEnrollment(Map<String, dynamic> inputs) async {
    final uri = Uri.parse('$_baseUrl$_predictEndpoint');

    try {
      final response = await _client
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(inputs),
          )
          .timeout(_requestTimeout);

      return _handleResponse(response);
    } on SocketException {
      throw const ApiException(
        'Network error: please check your internet connection and try again.',
      );
    } on TimeoutException {
      throw const ApiException(
        'Request timed out. The prediction server may be starting up. '
        'Please try again in a moment.',
      );
    } on http.ClientException {
      throw const ApiException(
        'Network error: unable to reach the prediction service.',
      );
    } on FormatException {
      throw const ApiException(
        'Invalid response from the prediction server.',
      );
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException(
        'An unexpected error occurred while contacting the prediction service.',
      );
    }
  }

  /// Parses the HTTP response and extracts the prediction value.
  double _handleResponse(http.Response response) {
    switch (response.statusCode) {
      case 200:
        return _parsePrediction(response.body);
      case 422:
        throw const ApiException(
          'Invalid input data. Please review your entries and try again.',
        );
      case 500:
        throw const ApiException(
          'The prediction server encountered an error. Please try again later.',
        );
      default:
        throw ApiException(
          'Unexpected server response (status ${response.statusCode}).',
        );
    }
  }

  /// Decodes the JSON response body and extracts
  /// `predicted_primary_enrollment` as a double.
  double _parsePrediction(String body) {
    try {
      final dynamic decoded = jsonDecode(body);

      if (decoded is! Map<String, dynamic>) {
        throw const ApiException(
          'Invalid response format from the prediction server.',
        );
      }

      if (!decoded.containsKey('predicted_primary_enrollment')) {
        throw const ApiException(
          'The server response is missing the prediction result.',
        );
      }

      final value = decoded['predicted_primary_enrollment'];

      if (value == null) {
        throw const ApiException(
          'The prediction result is invalid.',
        );
      }

      if (value is num) {
        return value.toDouble();
      }

      throw const ApiException(
        'The prediction result is not a valid number.',
      );
    } on FormatException {
      throw const ApiException(
        'Invalid response format from the prediction server.',
      );
    } on TypeError {
      throw const ApiException(
        'Invalid response format from the prediction server.',
      );
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException(
        'An unexpected error occurred while processing the prediction.',
      );
    }
  }
}
