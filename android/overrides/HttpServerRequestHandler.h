#pragma once
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <tuple>
#include <vector>
#include "json/json.h"
#include "CivetServer.h"

// Keep the upstream API adapter type, without desktop process metrics.
class HttpServerRequestHandler : public CivetServer {
 public:
  using httpFunctionReturn = std::tuple<int, std::map<std::string, std::string>, Json::Value>;
  using httpFunction = std::function<httpFunctionReturn(const mg_request_info*, const Json::Value&)>;
  HttpServerRequestHandler(std::map<std::string, httpFunction>& functions,
                           const std::vector<std::string>& options);
  ~HttpServerRequestHandler() override;
 private:
  std::vector<std::unique_ptr<CivetHandler>> handlers_;
};
