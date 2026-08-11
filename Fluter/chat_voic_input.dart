import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../services/api_service.dart';
import '../core/theme/app_theme.dart';

// ─── State ────────────────────────────────────────────────────────────────
class ChatMessage {
  final String role;
  final String content;
  final DateTime createdAt;
  ChatMessage({required this.role, required this.content, required this.createdAt});
}

class ChatNotifier extends StateNotifier<List<ChatMessage>> {
  final ApiService _api;
  ChatNotifier(this._api) : super([]) { _loadHistory(); }

  Future<void> _loadHistory() async {
    try {
      final history = await _api.getChatHistory();
      state = history.map((m) => ChatMessage(
        role: m['role'],
        content: m['content'],
        createdAt: DateTime.parse(m['created_at']),
      )).toList();
    } catch (_) {}
  }

  Future<String> sendMessage(String text) async {
    // Adiciona mensagem do usuário imediatamente
    state = [...state, ChatMessage(role: 'user', content: text, createdAt: DateTime.now())];
    try {
      final resp = await _api.sendMessage(text);
      final reply = resp['reply'] as String;
      state = [...state, ChatMessage(role: 'assistant', content: reply, createdAt: DateTime.now())];
      return reply;
    } catch (e) {
      final err = 'Desculpe, ocorreu um erro. Tente novamente.';
      state = [...state, ChatMessage(role: 'assistant', content: err, createdAt: DateTime.now())];
      return err;
    }
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, List<ChatMessage>>((ref) {
  return ChatNotifier(ref.read(apiServiceProvider));
});

// ─── Screen ──────────────────────────────────────────────────────────────
class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _stt = SpeechToText();
  final _tts = FlutterTts();
  bool _isListening = false;
  bool _isSending = false;
  bool _sttAvailable = false;

  @override
  void initState() {
    super.initState();
    _initSpeech();
    _initTts();
  }

  Future<void> _initSpeech() async {
    _sttAvailable = await _stt.initialize(
      onError: (e) => setState(() => _isListening = false),
    );
    setState(() {});
  }

  Future<void> _initTts() async {
    await _tts.setLanguage('pt-BR');
    await _tts.setSpeechRate(0.5);
    await _tts.setVolume(1.0);
  }

  void _toggleListening() {
    if (!_sttAvailable) return;
    if (_isListening) {
      _stt.stop();
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
      _stt.listen(
        onResult: (result) {
          _controller.text = result.recognizedWords;
          if (result.finalResult) {
            setState(() => _isListening = false);
          }
        },
        localeId: 'pt_BR',
      );
    }
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSending) return;
    _controller.clear();
    setState(() => _isSending = true);

    final reply = await ref.read(chatProvider.notifier).sendMessage(text);
    await _tts.speak(reply); // fala a resposta

    setState(() => _isSending = false);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _stt.stop();
    _tts.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(chatProvider);

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF0EA5E9), Color(0xFF6366F1)]),
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Center(child: Text('💎', style: TextStyle(fontSize: 18))),
            ),
            const SizedBox(width: 10),
            const Text('FINA'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.volume_up_rounded),
            onPressed: () => _tts.stop(),
            tooltip: 'Parar voz',
          ),
        ],
      ),
      body: Column(
        children: [
          // Mensagens
          Expanded(
            child: messages.isEmpty
                ? _buildWelcome()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: messages.length + (_isSending ? 1 : 0),
                    itemBuilder: (ctx, i) {
                      if (i == messages.length) return _buildTypingIndicator();
                      return _buildBubble(messages[i]);
                    },
                  ),
          ),
          // Input
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildWelcome() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
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
            const Text('Olá! Eu sou a FINA', style: TextStyle(
              fontSize: 22, fontWeight: FontWeight.w700, color: AppTheme.textPrimary,
            )),
            const SizedBox(height: 8),
            const Text(
              'Sua assistente financeira pessoal.\nPergunte sobre seus gastos, metas e saúde financeira!',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 14, height: 1.6),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBubble(ChatMessage msg) {
    final isUser = msg.role == 'user';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF0EA5E9), Color(0xFF6366F1)]),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Center(child: Text('💎', style: TextStyle(fontSize: 16))),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                gradient: isUser
                    ? const LinearGradient(colors: [AppTheme.primary, Color(0xFF059669)])
                    : null,
                color: isUser ? null : AppTheme.card,
                borderRadius: BorderRadius.only(
                  topLeft:     const Radius.circular(18),
                  topRight:    const Radius.circular(18),
                  bottomLeft:  Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
                ),
                border: isUser ? null : Border.all(color: AppTheme.cardBorder),
              ),
              child: Text(msg.content, style: const TextStyle(
                color: AppTheme.textPrimary, fontSize: 14, height: 1.6,
              )),
            ),
          ),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Row(
      children: [
        Container(
          width: 32, height: 32,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF0EA5E9), Color(0xFF6366F1)]),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Center(child: Text('💎', style: TextStyle(fontSize: 16))),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(18), topRight: Radius.circular(18),
              bottomRight: Radius.circular(18), bottomLeft: Radius.circular(4),
            ),
            border: Border.all(color: AppTheme.cardBorder),
          ),
          child: const Text('FINA está digitando...', style: TextStyle(
            color: AppTheme.textSecondary, fontSize: 13,
          )),
        ),
      ],
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      decoration: const BoxDecoration(
        color: AppTheme.card,
        border: Border(top: BorderSide(color: AppTheme.cardBorder)),
      ),
      child: Row(
        children: [
          // Mic
          GestureDetector(
            onTap: _toggleListening,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 44, height: 44,
              decoration: BoxDecoration(
                color: _isListening ? AppTheme.primary : AppTheme.surface,
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: _isListening ? AppTheme.primary : AppTheme.cardBorder),
              ),
              child: Icon(
                _isListening ? Icons.mic : Icons.mic_none_rounded,
                color: _isListening ? Colors.white : AppTheme.textSecondary,
                size: 20,
              ),
            ),
          ),
          const SizedBox(width: 10),
          // TextField
          Expanded(
            child: TextField(
              controller: _controller,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
              decoration: InputDecoration(
                hintText: _isListening ? 'Ouvindo...' : 'Pergunte algo à FINA...',
                hintStyle: const TextStyle(color: AppTheme.textSecondary),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: const BorderSide(color: AppTheme.cardBorder),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: const BorderSide(color: AppTheme.cardBorder),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: const BorderSide(color: AppTheme.primary, width: 2),
                ),
                filled: true, fillColor: AppTheme.surface,
              ),
              onSubmitted: (_) => _sendMessage(),
              maxLines: 3, minLines: 1,
            ),
          ),
          const SizedBox(width: 10),
          // Send
          GestureDetector(
            onTap: _isSending ? null : _sendMessage,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 44, height: 44,
              decoration: BoxDecoration(
                gradient: _isSending ? null : const LinearGradient(
                  colors: [AppTheme.primary, Color(0xFF6366F1)],
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                ),
                color: _isSending ? AppTheme.cardBorder : null,
                borderRadius: BorderRadius.circular(22),
              ),
              child: Icon(
                _isSending ? Icons.hourglass_bottom_rounded : Icons.send_rounded,
                color: Colors.white, size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }
}