async def ingest_document(
    doc: schemas.Document,
    service: IngestionService = Depends(deps.get_ingestion_service),
) -> Response:
    await process_document_with_service(doc, service)
    return Response(status_code=status.HTTP_202_ACCEPTED)
