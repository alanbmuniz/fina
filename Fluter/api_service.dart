import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _baseUrl = 'https://api.fina.com.br/api/v1'; // troque para seu domínio
const _storage = FlutterSecureStorage();

// ─── Dio Provider ──────────────────────────────────────────────────────────
final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: _baseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Content-Type': 'application/json'},
  ));

  dio.interceptors.add(_AuthInterceptor(dio));
  return dio;
});

// ─── Auth Interceptor (injeta token + refresh automático) ─────────────────
class _AuthInterceptor extends Interceptor {
  final Dio _dio;
  _AuthInterceptor(this._dio);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _storage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Tenta refresh automático
      final refreshed = await _tryRefresh();
      if (refreshed) {
        final token = await _storage.read(key: 'access_token');
        err.requestOptions.headers['Authorization'] = 'Bearer $token';
        final retry = await _dio.fetch(err.requestOptions);
        return handler.resolve(retry);
      }
    }
    handler.next(err);
  }

  Future<bool> _tryRefresh() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final resp = await Dio().post('$_baseUrl/auth/refresh',
          data: {'refresh_token': refreshToken});
      await _storage.write(key: 'access_token',  value: resp.data['access_token']);
      await _storage.write(key: 'refresh_token', value: resp.data['refresh_token']);
      return true;
    } catch (_) { return false; }
  }
}

// ─── API Service ──────────────────────────────────────────────────────────
class ApiService {
  final Dio _dio;
  ApiService(this._dio);

  // Auth
  Future<Map<String, dynamic>> login(String email, String password) async {
    final resp = await _dio.post('/auth/login', data: {'email': email, 'password': password});
    await _saveTokens(resp.data);
    return resp.data;
  }

  Future<Map<String, dynamic>> register(Map<String, dynamic> data) async {
    final resp = await _dio.post('/auth/register', data: data);
    await _saveTokens(resp.data);
    return resp.data;
  }

  Future<void> logout() async {
    final rt = await _storage.read(key: 'refresh_token');
    if (rt != null) {
      try { await _dio.post('/auth/logout', data: {'refresh_token': rt}); } catch (_) {}
    }
    await _storage.deleteAll();
  }

  // User
  Future<Map<String, dynamic>> getMe() async {
    final resp = await _dio.get('/users/me');
    return resp.data;
  }

  // Transactions
  Future<List<dynamic>> getTransactions({int? month, int? year}) async {
    final resp = await _dio.get('/transactions', queryParameters: {
      if (month != null) 'month': month,
      if (year  != null) 'year':  year,
    });
    return resp.data;
  }

  Future<Map<String, dynamic>> createTransaction(Map<String, dynamic> data) async {
    final resp = await _dio.post('/transactions', data: data);
    return resp.data;
  }

  Future<Map<String, dynamic>> monthlySummary(int year, int month) async {
    final resp = await _dio.get('/transactions/summary/monthly',
        queryParameters: {'year': year, 'month': month});
    return resp.data;
  }

  // Cards
  Future<List<dynamic>> getCards() async {
    final resp = await _dio.get('/cards');
    return resp.data;
  }

  Future<Map<String, dynamic>> createCard(Map<String, dynamic> data) async {
    final resp = await _dio.post('/cards', data: data);
    return resp.data;
  }

  Future<Map<String, dynamic>> syncCard(int cardId) async {
    final resp = await _dio.post('/cards/$cardId/sync');
    return resp.data;
  }

  Future<String> getConnectToken() async {
    final resp = await _dio.get('/cards/openfinance/connect-token');
    return resp.data['connect_token'];
  }

  // Goals
  Future<List<dynamic>> getGoals() async {
    final resp = await _dio.get('/goals');
    return resp.data;
  }

  Future<Map<String, dynamic>> createGoal(Map<String, dynamic> data) async {
    final resp = await _dio.post('/goals', data: data);
    return resp.data;
  }

  Future<Map<String, dynamic>> updateGoal(int id, Map<String, dynamic> data) async {
    final resp = await _dio.patch('/goals/$id', data: data);
    return resp.data;
  }

  Future<Map<String, dynamic>> goalProjection(int id, double monthly) async {
    final resp = await _dio.get('/goals/$id/projection',
        queryParameters: {'monthly_contribution': monthly});
    return resp.data;
  }

  // Chat IA
  Future<Map<String, dynamic>> sendMessage(String message) async {
    final resp = await _dio.post('/chat', data: {'message': message});
    return resp.data;
  }

  Future<List<dynamic>> getChatHistory() async {
    final resp = await _dio.get('/chat/history');
    return resp.data;
  }

  // Health Score
  Future<Map<String, dynamic>> getFinancialHealth() async {
    final resp = await _dio.get('/reports/health');
    return resp.data;
  }

  // Internos
  Future<void> _saveTokens(Map<String, dynamic> data) async {
    await _storage.write(key: 'access_token',  value: data['access_token']);
    await _storage.write(key: 'refresh_token', value: data['refresh_token']);
  }
}

final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService(ref.read(dioProvider));
});