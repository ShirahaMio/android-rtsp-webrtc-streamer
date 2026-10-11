#include "HttpServerRequestHandler.h"
#include <exception>

namespace {
bool respond(mg_connection* connection, int code, const std::string& body,
             const std::map<std::string, std::string>& headers = {}) {
  mg_printf(connection,
            "HTTP/1.1 %d %s\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type\r\n"
            "Access-Control-Allow-Private-Network: true\r\n"
            "Cache-Control: no-store\r\n"
            "Content-Length: %zu\r\n", code,
            mg_get_response_code_text(connection, code), body.size());
  if (!headers.count("Content-Type"))
    mg_printf(connection, "Content-Type: application/json\r\n");
  for (const auto& [key, value] : headers)
    mg_printf(connection, "%s: %s\r\n", key.c_str(), value.c_str());
  mg_printf(connection, "\r\n");
  if (!body.empty()) mg_write(connection, body.data(), body.size());
  return true;
}

class ApiHandler final : public CivetHandler {
 public:
  explicit ApiHandler(HttpServerRequestHandler::httpFunction fn) : function_(std::move(fn)) {}
  bool handleGet(CivetServer*, mg_connection* c) override { return handle(c); }
  bool handlePost(CivetServer*, mg_connection* c) override { return handle(c); }
  bool handlePatch(CivetServer*, mg_connection* c) override { return handle(c); }
  bool handleDelete(CivetServer*, mg_connection* c) override { return handle(c); }
  bool handleOptions(CivetServer*, mg_connection* c) override { return respond(c, 204, ""); }
 private:
  bool handle(mg_connection* connection) {
    try {
      const auto* request = mg_get_request_info(connection);
      if (request->content_length > 1024 * 1024)
        return respond(connection, 413, "{\"error\":\"Request too large\"}");
      const std::string method(request->request_method);
      if (request->content_length < 0 && (method == "POST" || method == "PATCH"))
        return respond(connection, 411, "{\"error\":\"Content-Length required\"}");
      Json::Value input;
      if (request->content_length > 0) {
        std::string data(static_cast<size_t>(request->content_length), '\0');
        size_t received = 0;
        while (received < data.size()) {
          const int count = mg_read(connection, data.data() + received, data.size() - received);
          if (count <= 0) return respond(connection, 400, "{\"error\":\"Incomplete body\"}");
          received += static_cast<size_t>(count);
        }
        Json::CharReaderBuilder builder;
        std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
        std::string errors;
        if (!reader->parse(data.data(), data.data() + data.size(), &input, &errors))
          input = data; // WHEP uses SDP rather than JSON.
      }
      auto [code, headers, result] = function_(request, input);
      if (result.isNull()) return respond(connection, 500, "{\"error\":\"Operation failed\"}");
      Json::StreamWriterBuilder writer;
      writer["indentation"] = "";
      std::string body = result.isString() ? result.asString() : Json::writeString(writer, result);
      return respond(connection, code, body, headers);
    } catch (const std::exception&) {
      return respond(connection, 500, "{\"error\":\"Invalid request or server error\"}");
    }
  }
  HttpServerRequestHandler::httpFunction function_;
};
}  // namespace

HttpServerRequestHandler::HttpServerRequestHandler(
    std::map<std::string, httpFunction>& functions, const std::vector<std::string>& options)
    : CivetServer(options) {
  for (const auto& [path, function] : functions) {
    auto handler = std::make_unique<ApiHandler>(function);
    addHandler(path, handler.get());
    handlers_.push_back(std::move(handler));
  }
}

HttpServerRequestHandler::~HttpServerRequestHandler() {
  close(); // Join HTTP workers before handlers or PeerConnectionManager are destroyed.
}
