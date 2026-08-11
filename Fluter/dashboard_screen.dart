import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../core/theme/app_theme.dart';

final dashboardProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final now = DateTime.now();
  final summary = await api.monthlySummary(now.year, now.month);
  final health  = await api.getFinancialHealth();
  final cards   = await api.getCards();
  return {'summary': summary, 'health': health, 'cards': cards};
});

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  static final _currency = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(dashboardProvider);

    return Scaffold(
      backgroundColor: AppTheme.surface,
      body: SafeArea(
        child: data.when(
          loading: () => const Center(child: CircularProgressIndicator(color: AppTheme.primary)),
          error: (e, _) => Center(child: Text('Erro: $e', style: const TextStyle(color: AppTheme.danger))),
          data: (d) => RefreshIndicator(
            onRefresh: () => ref.refresh(dashboardProvider.future),
            color: AppTheme.primary,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHeader(d),
                  const SizedBox(height: 20),
                  _buildHealthScore(d['health']),
                  const SizedBox(height: 20),
                  _buildSummaryCards(d['summary']),
                  const SizedBox(height: 24),
                  _buildCategoryChart(d['summary']['by_category'] ?? {}),
                  const SizedBox(height: 24),
                  _buildCards(d['cards']),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(Map d) {
    final h = d['health'];
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Visão Geral', style: TextStyle(
                fontSize: 22, fontWeight: FontWeight.w700, color: AppTheme.textPrimary,
              )),
              Text(
                DateFormat("MMMM 'de' yyyy", 'pt_BR').format(DateTime.now()),
                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: _healthColor(h['score']).withOpacity(0.15),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: _healthColor(h['score']).withOpacity(0.3)),
          ),
          child: Text(h['label'] ?? '', style: TextStyle(
            color: _healthColor(h['score']), fontWeight: FontWeight.w700, fontSize: 13,
          )),
        ),
      ],
    );
  }

  Widget _buildHealthScore(Map h) {
    final score = (h['score'] as num).toDouble();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [_healthColor(score.toInt()).withOpacity(0.15), Colors.transparent],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _healthColor(score.toInt()).withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Score Financeiro', style: TextStyle(
                color: AppTheme.textSecondary, fontSize: 13, fontWeight: FontWeight.w600,
              )),
              const Spacer(),
              Text('${score.toInt()}/100', style: TextStyle(
                color: _healthColor(score.toInt()), fontSize: 22, fontWeight: FontWeight.w800,
              )),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: score / 100,
              minHeight: 10,
              backgroundColor: AppTheme.cardBorder,
              valueColor: AlwaysStoppedAnimation(_healthColor(score.toInt())),
            ),
          ),
          if ((h['alerts'] as List).isNotEmpty) ...[
            const SizedBox(height: 12),
            ...(h['alerts'] as List).map((a) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(a.toString(), style: const TextStyle(
                color: AppTheme.warning, fontSize: 12,
              )),
            )),
          ],
        ],
      ),
    );
  }

  Widget _buildSummaryCards(Map s) {
    return Row(
      children: [
        Expanded(child: _metricCard('Receitas', s['total_income'], AppTheme.income, '↑')),
        const SizedBox(width: 12),
        Expanded(child: _metricCard('Despesas', s['total_expense'], AppTheme.expense, '↓')),
        const SizedBox(width: 12),
        Expanded(child: _metricCard('Saldo', s['balance'],
          (s['balance'] as num) >= 0 ? AppTheme.income : AppTheme.danger, '=')),
      ],
    );
  }

  Widget _metricCard(String label, dynamic value, Color color, String icon) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(icon, style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
          const SizedBox(height: 2),
          Text(
            _currency.format((value as num).toDouble()),
            style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w700),
            maxLines: 1, overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryChart(Map categories) {
    if (categories.isEmpty) return const SizedBox();
    final entries = categories.entries.toList()
      ..sort((a, b) => (b.value as num).compareTo(a.value as num));
    final top = entries.take(5).toList();
    final colors = [
      AppTheme.primary, AppTheme.secondary,
      AppTheme.warning, AppTheme.danger, const Color(0xFF06B6D4),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Gastos por Categoria', style: TextStyle(
          fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textPrimary,
        )),
        const SizedBox(height: 14),
        SizedBox(
          height: 180,
          child: PieChart(PieChartData(
            sections: List.generate(top.length, (i) {
              final val = (top[i].value as num).toDouble();
              return PieChartSectionData(
                value: val,
                color: colors[i % colors.length],
                title: '',
                radius: 55,
              );
            }),
            sectionsSpace: 3,
            centerSpaceRadius: 45,
          )),
        ),
        const SizedBox(height: 14),
        ...List.generate(top.length, (i) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            children: [
              Container(width: 12, height: 12, decoration: BoxDecoration(
                color: colors[i % colors.length],
                borderRadius: BorderRadius.circular(3),
              )),
              const SizedBox(width: 10),
              Expanded(child: Text(top[i].key, style: const TextStyle(
                color: AppTheme.textPrimary, fontSize: 13,
              ))),
              Text(_currency.format((top[i].value as num).toDouble()),
                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
          ),
        )),
      ],
    );
  }

  Widget _buildCards(List cards) {
    if (cards.isEmpty) return const SizedBox();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Cartões de Crédito', style: TextStyle(
          fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textPrimary,
        )),
        const SizedBox(height: 14),
        ...cards.map((c) {
          final used  = (c['used_amount']  as num).toDouble();
          final limit = (c['limit_amount'] as num).toDouble();
          final pct   = limit > 0 ? used / limit : 0.0;
          final color = pct > 0.8 ? AppTheme.danger : pct > 0.5 ? AppTheme.warning : AppTheme.income;
          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.cardBorder),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(child: Text(c['name'], style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 15, color: AppTheme.textPrimary,
                    ))),
                    Text('${(pct * 100).toStringAsFixed(0)}%',
                      style: TextStyle(color: color, fontWeight: FontWeight.w700)),
                  ],
                ),
                const SizedBox(height: 10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: pct, minHeight: 8,
                    backgroundColor: AppTheme.cardBorder,
                    valueColor: AlwaysStoppedAnimation(color),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Usado: ${_currency.format(used)}',
                      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                    Text('Limite: ${_currency.format(limit)}',
                      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ],
            ),
          );
        }),
      ],
    );
  }

  Color _healthColor(int score) =>
    score >= 80 ? AppTheme.income :
    score >= 60 ? AppTheme.warning :
    score >= 40 ? const Color(0xFFF97316) : AppTheme.danger;
}