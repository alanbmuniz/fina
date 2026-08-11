// ════════════════════════════════════════════════════════════════
// router/app_router.dart
// ════════════════════════════════════════════════════════════════
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../screens/chat_screen.dart';
import '../screens/dashboard_screen.dart';
import '../screens/login_screen.dart';
import '../screens/home_shell.dart';

const _storage = FlutterSecureStorage();

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/chat',
    redirect: (context, state) async {
      final token = await _storage.read(key: 'access_token');
      final isAuth = token != null;
      final isLogin = state.matchedLocation == '/login';
      if (!isAuth && !isLogin) return '/login';
      if (isAuth && isLogin) return '/chat';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      ShellRoute(
        builder: (_, __, child) => HomeShell(child: child),
        routes: [
          GoRoute(path: '/chat',      builder: (_, __) => const ChatScreen()),
          GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
          GoRoute(path: '/add',       builder: (_, __) => const AddTransactionScreen()),
          GoRoute(path: '/goals',     builder: (_, __) => const GoalsScreen()),
          GoRoute(path: '/cards',     builder: (_, __) => const CardsScreen()),
        ],
      ),
    ],
  );
});

// ════════════════════════════════════════════════════════════════
// screens/home_shell.dart — Bottom Navigation
// ════════════════════════════════════════════════════════════════
class HomeShell extends StatelessWidget {
  final Widget child;
  const HomeShell({super.key, required this.child});

  static const _tabs = [
    _Tab('/chat',      Icons.chat_bubble_outline_rounded, Icons.chat_bubble_rounded,       'Chat'),
    _Tab('/dashboard', Icons.bar_chart_outlined,          Icons.bar_chart_rounded,          'Dashboard'),
    _Tab('/add',       Icons.add_circle_outline_rounded,  Icons.add_circle_rounded,         'Lançar'),
    _Tab('/goals',     Icons.flag_outlined,               Icons.flag_rounded,               'Metas'),
    _Tab('/cards',     Icons.credit_card_outlined,        Icons.credit_card_rounded,        'Cartões'),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final currentIndex = _tabs.indexWhere((t) => location.startsWith(t.path)).clamp(0, 4);

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: Color(0xFF334155), width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: currentIndex,
          onTap: (i) => context.go(_tabs[i].path),
          items: _tabs.map((t) => BottomNavigationBarItem(
            icon: Icon(t.icon),
            activeIcon: Icon(t.activeIcon),
            label: t.label,
          )).toList(),
        ),
      ),
    );
  }
}

class _Tab {
  final String path;
  final IconData icon;
  final IconData activeIcon;
  final String label;
  const _Tab(this.path, this.icon, this.activeIcon, this.label);
}

// ════════════════════════════════════════════════════════════════
// screens/login_screen.dart
// ════════════════════════════════════════════════════════════════
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailCtrl    = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _loading = false;
  bool _isRegister = false;
  String? _error;

  Future<void> _submit() async {
    setState(() { _loading = true; _error = null; });
    try {
      final api = ref.read(apiServiceProvider);
      if (_isRegister) {
        await api.register({'email': _emailCtrl.text, 'password': _passwordCtrl.text, 'name': 'Usuário'});
      } else {
        await api.login(_emailCtrl.text, _passwordCtrl.text);
      }
      if (mounted) context.go('/chat');
    } catch (e) {
      setState(() => _error = 'Credenciais inválidas. Tente novamente.');
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF020617),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: Column(
            children: [
              const SizedBox(height: 60),
              Container(
                width: 80, height: 80,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF10B981), Color(0xFF6366F1)],
                    begin: Alignment.topLeft, end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(40),
                ),
                child: const Center(child: Text('💎', style: TextStyle(fontSize: 40))),
              ),
              const SizedBox(height: 20),
              const Text('FINA', style: TextStyle(
                fontSize: 32, fontWeight: FontWeight.w800,
                foreground: Paint()..shader = const LinearGradient(
                  colors: [Color(0xFF10B981), Color(0xFF6366F1)],
                ).createShader(Rect.fromLTWH(0, 0, 100, 40)),
              )),
              const SizedBox(height: 8),
              const Text('Sua assistente financeira com IA', style: TextStyle(
                color: Color(0xFF94A3B8), fontSize: 14,
              )),
              const SizedBox(height: 48),
              TextField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  labelText: 'E-mail',
                  prefixIcon: Icon(Icons.email_outlined, color: Color(0xFF94A3B8)),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  labelText: 'Senha',
                  prefixIcon: Icon(Icons.lock_outline_rounded, color: Color(0xFF94A3B8)),
                ),
                onSubmitted: (_) => _submit(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13)),
              ],
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
                      : Text(_isRegister ? 'Criar conta' : 'Entrar'),
                ),
              ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () => setState(() => _isRegister = !_isRegister),
                child: Text(
                  _isRegister ? 'Já tenho conta → Entrar' : 'Não tenho conta → Cadastrar',
                  style: const TextStyle(color: Color(0xFF10B981)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════
// screens/add_transaction_screen.dart (stub importável)
// ════════════════════════════════════════════════════════════════
class AddTransactionScreen extends ConsumerStatefulWidget {
  const AddTransactionScreen({super.key});
  @override
  ConsumerState<AddTransactionScreen> createState() => _AddTransactionState();
}

class _AddTransactionState extends ConsumerState<AddTransactionScreen> {
  final _descCtrl   = TextEditingController();
  final _amountCtrl = TextEditingController();
  String _type = 'expense';
  String _category = 'Outros';
  bool _loading = false;

  static const _cats = ['Alimentação','Moradia','Transporte','Saúde','Lazer','Educação','Vestuário','Outros'];

  Future<void> _save() async {
    if (_descCtrl.text.isEmpty || _amountCtrl.text.isEmpty) return;
    setState(() => _loading = true);
    try {
      await ref.read(apiServiceProvider).createTransaction({
        'type': _type,
        'description': _descCtrl.text,
        'amount': double.parse(_amountCtrl.text.replaceAll(',', '.')),
        'category': _category,
        'date': DateTime.now().toIso8601String(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ Lançamento salvo!'), backgroundColor: Color(0xFF10B981)));
        _descCtrl.clear(); _amountCtrl.clear();
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Erro ao salvar'), backgroundColor: Color(0xFFEF4444)));
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final isIncome = _type == 'income';
    return Scaffold(
      appBar: AppBar(title: const Text('Novo Lançamento')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Row(children: [
              Expanded(child: _typeBtn('Receita', 'income', isIncome, const Color(0xFF10B981))),
              const SizedBox(width: 12),
              Expanded(child: _typeBtn('Despesa', 'expense', !isIncome, const Color(0xFFEF4444))),
            ]),
            const SizedBox(height: 20),
            TextField(controller: _descCtrl, style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(labelText: 'Descrição', prefixIcon: Icon(Icons.edit_outlined))),
            const SizedBox(height: 16),
            TextField(controller: _amountCtrl, keyboardType: TextInputType.number,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(labelText: 'Valor (R\$)', prefixIcon: Icon(Icons.attach_money_rounded))),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _category,
              dropdownColor: const Color(0xFF1E293B),
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(labelText: 'Categoria'),
              items: _cats.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
              onChanged: (v) => setState(() => _category = v!),
            ),
            const SizedBox(height: 28),
            SizedBox(width: double.infinity, child: ElevatedButton(
              onPressed: _loading ? null : _save,
              style: ElevatedButton.styleFrom(
                backgroundColor: isIncome ? const Color(0xFF10B981) : const Color(0xFFEF4444),
              ),
              child: _loading
                  ? const CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
                  : Text(isIncome ? '+ Adicionar Receita' : '+ Adicionar Despesa'),
            )),
          ],
        ),
      ),
    );
  }

  Widget _typeBtn(String label, String type, bool active, Color color) {
    return GestureDetector(
      onTap: () => setState(() => _type = type),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: active ? color.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: active ? color : const Color(0xFF334155), width: 2),
        ),
        child: Center(child: Text(label, style: TextStyle(
          color: active ? color : const Color(0xFF64748B), fontWeight: FontWeight.w700,
        ))),
      ),
    );
  }
}

// ─── Stubs (implementar conforme modelo acima) ────────────────────────────
class GoalsScreen extends ConsumerWidget {
  const GoalsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
    Scaffold(appBar: AppBar(title: const Text('Metas')),
      body: const Center(child: Text('Metas — em construção', style: TextStyle(color: Color(0xFF94A3B8)))));
}

class CardsScreen extends ConsumerWidget {
  const CardsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
    Scaffold(appBar: AppBar(title: const Text('Cartões')),
      body: const Center(child: Text('Cartões — em construção', style: TextStyle(color: Color(0xFF94A3B8)))));
}

// Imports necessários para o arquivo funcionar como stub
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';