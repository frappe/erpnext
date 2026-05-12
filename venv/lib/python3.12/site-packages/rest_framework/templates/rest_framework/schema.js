var codec = new window.coreapi.codecs.CoreJSONCodec()
var coreJSON = window.atob('{{ schema }}')
window.schema = codec.decode(coreJSON)
