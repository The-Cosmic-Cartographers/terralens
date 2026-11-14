const productLabels = {
  reanalysis: 'Model reanalysis',
  satellite: 'Satellite estimate',
  land_model: 'Land model',
}

function ProductBadge({ type }) {
  return (
    <span className="product-badge">
      <span className="badge-dot" />
      {productLabels[type] || type}
    </span>
  )
}

export default ProductBadge
